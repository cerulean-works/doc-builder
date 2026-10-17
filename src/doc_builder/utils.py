# Copyright 2021 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
from collections.abc import Sequence
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

DOC_BUILDER_CACHE = os.getenv(
    "DOC_BUILDER_CACHE", os.path.join(os.path.expanduser(os.getenv("XDG_CACHE_HOME", "~/.cache")), "doc-builder")
)
DEFAULT_REPO_OWNER = "cerulean-works"
DEFAULT_SITE_URL = "https://docs.cerulean.works"


def get_default_branch_name(repo_folder):
    config = get_doc_config()
    if config is not None and hasattr(config, "default_branch_name"):
        return config.default_branch_name
    try:
        p = subprocess.run(
            "git symbolic-ref refs/remotes/origin/HEAD".split(),
            capture_output=True,
            check=True,
            encoding="utf-8",
            cwd=repo_folder,
        )
        branch = p.stdout.strip().split("/")[-1]
        return branch
    except Exception:
        # Just in case git is not installed, we need a default
        return "main"


doc_config = None


def read_doc_config(doc_folder):
    """
    Execute the `_config.py` file inside the doc source directory and executes it as a Python module.
    """
    global doc_config

    if os.path.isfile(os.path.join(doc_folder, "_config.py")):
        loader = importlib.machinery.SourceFileLoader("doc_config", os.path.join(doc_folder, "_config.py"))
        spec = importlib.util.spec_from_loader("doc_config", loader)
        doc_config = importlib.util.module_from_spec(spec)
        loader.exec_module(doc_config)
    else:
        doc_config = None


def get_doc_config():
    """
    Returns the `doc_config` if it has been loaded.
    """
    return doc_config


def get_project_info(project, repo=None):
    """
    Project metadata (`_project.json`, contracts C2/C3), read from `_config.py` (`project_title`,
    `project_description`, `repo`). An explicit `repo` (`--repo`) wins over the config; the fallback is
    `cerulean-works/<project>`.
    """
    config = get_doc_config()
    repo = repo or getattr(config, "repo", None) or f"{DEFAULT_REPO_OWNER}/{project}"
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ValueError(f"`repo` must look like `owner/name`, got `{repo}`.")
    return {
        "name": project,
        "title": getattr(config, "project_title", None) or project,
        "description": getattr(config, "project_description", None) or "",
        "repo": repo,
    }


def find_root_git(folder):
    "Finds the first parent folder who is a git directory or returns None if there is no git directory."
    folder = Path(folder).absolute()
    while folder != folder.parent and not (folder / ".git").exists():
        folder = folder.parent
    return folder if folder != folder.parent else None


def is_watchdog_available():
    """
    Checks if soft dependency `watchdog` exists.
    """
    return importlib.util.find_spec("watchdog") is not None


def is_doc_builder_repo(path):
    """
    Detects whether a folder is the `doc_builder` or not.
    """
    pyproject_file = Path(path) / "pyproject.toml"
    if not pyproject_file.exists():
        return False
    content = pyproject_file.read_text(encoding="utf-8")
    return re.search(r"""^name\s*=\s*["']cerulean-doc-builder["']""", content, flags=re.MULTILINE) is not None


def locate_kit_folder():
    """
    Returns the location of the `kit` folder of `doc-builder`.

    Will clone the doc-builder repo and cache it, if it's not found.
    """
    # First try: let's search where the module is.
    repo_root = Path(__file__).parent.parent.parent
    kit_folder = repo_root / "kit"
    if kit_folder.is_dir():
        return kit_folder

    # Second try, maybe we are inside the doc-builder repo
    current_dir = Path.cwd()
    while current_dir.parent != current_dir and not (current_dir / ".git").is_dir():
        current_dir = current_dir.parent
    kit_folder = current_dir / "kit"
    if kit_folder.is_dir() and is_doc_builder_repo(current_dir):
        return kit_folder

    # Otherwise, let's clone the repo and cache it.
    return Path(get_cached_repo()) / "kit"


def get_cached_repo():
    """
    Clone and cache the `doc-builder` repo.
    """
    os.makedirs(DOC_BUILDER_CACHE, exist_ok=True)
    cache_repo_path = Path(DOC_BUILDER_CACHE) / "doc-builder-repo"
    if not cache_repo_path.is_dir():
        print(
            "To build the HTML doc, we need the kit subfolder of the `doc-builder` repo. Cloning it and caching at "
            f"{cache_repo_path}."
        )
        _ = subprocess.run(
            f"git clone https://github.com/{DEFAULT_REPO_OWNER}/doc-builder.git".split(),
            stderr=subprocess.PIPE,
            check=True,
            encoding="utf-8",
            cwd=DOC_BUILDER_CACHE,
        )
        shutil.move(Path(DOC_BUILDER_CACHE) / "doc-builder", cache_repo_path)
    else:
        _ = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            check=True,
            encoding="utf-8",
            cwd=cache_repo_path,
        )
    return cache_repo_path


def page_route(section, page_local):
    """
    Path of a page relative to the `/<project>/<version>/` base, without trailing slash (contract C1): `<local>`
    maps to `<section>/<local>`, except that `index` (or `<dir>/index`) maps to its directory.
    """
    local = page_local.strip("/")
    if local == "index":
        local = ""
    elif local.endswith("/index"):
        local = local[: -len("/index")]
    return f"{section}/{local}" if local else section


def doc_url(project, version, section, page_local, anchor=None):
    """
    Absolute path of a page, always with a trailing slash: `/<project>/<version>/<section>/<page>/[#<anchor>]`.
    """
    url = f"/{project}/{version}/{page_route(section, page_local)}/"
    return f"{url}#{anchor}" if anchor else url


def doc_md_url(project, version, section, page_local):
    """
    Absolute path of the Markdown export of a page: its URL without the trailing slash, plus `.md`
    (`/<p>/<v>/guide/quickstart/` -> `/<p>/<v>/guide/quickstart.md`, `/<p>/<v>/guide/` -> `/<p>/<v>/guide.md`).
    """
    return f"/{project}/{version}/{page_route(section, page_local)}.md"


def resolve_page_url(target, page_info):
    """
    Absolute URL of the page `target` (a path relative to the docs folder, without extension) if `page_info["page_map"]`
    (page local -> section) knows it, else `None`. `foo` also resolves to `foo/index`.
    """
    page_map = page_info.get("page_map") or {}
    for local in (target, f"{target}/index" if target else "index"):
        if local in page_map:
            return doc_url(page_info["package_name"], page_info.get("version", "main"), page_map[local], local)
    return None


_SCRIPT_BLOCK_RE = re.compile(r"^\s*<script\b[^>]*>.*?</script>\s*", re.DOTALL)
_SCRIPT_MARKERS = ("HF_DOC_BODY_START", "HF_DOC_BODY_END")
_DOCBODY_LINE_RE = re.compile(r"^\s*HF_DOC_BODY_(?:START|END)\s*$", re.MULTILINE)


def convert_mdx_to_markdown_text(content: str) -> str:
    """Reduce MDX content to Markdown-only text suitable for distribution."""

    content = _SCRIPT_BLOCK_RE.sub("", content, count=1)

    heading_match = re.search(r"^#", content, flags=re.MULTILINE)
    if heading_match:
        cleaned = content[heading_match.start() :]
    else:
        index_candidates = [content.find(marker) for marker in _SCRIPT_MARKERS if marker in content]
        index_candidates = [idx for idx in index_candidates if idx >= 0]
        cleaned = content[min(index_candidates) :] if index_candidates else content

    cleaned = _DOCBODY_LINE_RE.sub("", cleaned)
    cleaned = cleaned.replace("HF_DOC_BODY_START", "").replace("HF_DOC_BODY_END", "")
    return cleaned.lstrip().rstrip()


def mdx_to_markdown(content: str) -> str:
    """The clean Markdown export (contract C1) of a generated `.mdx` page."""
    return strip_html_from_markdown(convert_mdx_to_markdown_text(content))


def write_llms_feeds(
    output_dir: Path,
    markdown_items: Sequence[tuple[str, str]],
    project: str,
    version: str,
    site_url: str = DEFAULT_SITE_URL,
    title: str | None = None,
):
    """
    Generate `llms.txt` and `llms-full.txt` in `output_dir`.

    `markdown_items` are `(path, markdown)` tuples, in the order they should be listed, with `path` relative to the
    `/<project>/<version>/` base (e.g. `guide/quickstart.md`).
    """
    output_dir = Path(output_dir)
    markdown_items = [(str(path).replace(os.sep, "/"), text) for path, text in markdown_items if path]
    if not markdown_items:
        return

    base_url = f"{site_url.rstrip('/')}/{quote(project, safe='')}/{quote(version, safe='')}"

    def extract_title(markdown_text: str, fallback: str) -> str:
        for line in markdown_text.splitlines():
            if line.startswith("#"):
                # drop custom `[[anchor]]` suffixes
                return re.sub(r"\[\[[^\]]*\]\]\s*$", "", line.lstrip("#")).strip() or fallback
        return fallback

    bullet_lines: list[str] = []
    sections: list[str] = []

    for relative_path, markdown_text in markdown_items:
        url = f"{base_url}/{quote(relative_path.lstrip('/'), safe='/')}"
        fallback_title = Path(relative_path).name.replace(".md", "").replace("-", " ").replace("_", " ").title()
        page_title = extract_title(markdown_text, fallback_title)
        bullet_lines.append(f"- [{page_title}]({url})")
        markdown_body = markdown_text.strip()
        sections.extend(
            [f"### {page_title}", url, "", markdown_body, ""] if markdown_body else [f"### {page_title}", url, ""]
        )

    header_lines = [f"# {title or project}", "", "## Docs", ""]
    llms_lines = header_lines + bullet_lines + [""]
    llms_full_lines = header_lines + bullet_lines + [""] + sections

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.joinpath("llms.txt").write_text("\n".join(llms_lines).rstrip() + "\n", encoding="utf-8")
    output_dir.joinpath("llms-full.txt").write_text("\n".join(llms_full_lines).rstrip() + "\n", encoding="utf-8")


_HTML_TAGS = frozenset(
    """
    a abbr address area article aside audio b base bdi bdo blockquote body br button canvas caption cite code col
    colgroup data datalist dd del details dfn dialog div dl dt em embed fieldset figcaption figure footer form h1 h2
    h3 h4 h5 h6 head header hgroup hr html i iframe img input ins kbd label legend li link main map mark math menu
    meta meter nav noscript object ol optgroup option output p param picture pre progress q rp rt ruby s samp script
    section select slot small source span strong style sub summary sup svg table tbody td template textarea tfoot th
    thead time title tr track u ul var video wbr center font
    """.split()
)


class HTMLStripper(HTMLParser):
    """Helper class to strip HTML tags while preserving text content."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_data(self):
        return "".join(self.text)


def strip_html_tags(text: str) -> str:
    """Strip HTML tags from text while preserving content."""
    stripper = HTMLStripper()
    stripper.feed(text)
    return stripper.get_data()


def _extract_svelte_prop(props: str, prop_name: str):
    """
    Read the JSON value of a `name={<json>}` svelte attribute out of an opening-tag
    attribute string, or return `None` if the prop is absent or malformed.

    The JSON is parsed with `raw_decode` so values containing `}` or `>` (type
    annotations, defaults, ...) don't confuse the extraction.
    """
    match = re.search(rf"\b{prop_name}=\{{", props)
    if match is None:
        return None
    try:
        value, end = json.JSONDecoder().raw_decode(props, match.end())
    except ValueError:
        return None
    if not props[end:].lstrip().startswith("}"):
        return None
    return value


def _extract_section(block: str, tag: str):
    """Return the (stripped) content of `<tag>...</tag>` in `block`, or `None`."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.DOTALL)
    return match.group(1).strip() if match else None


def extract_docstring_info(docstring_block: str) -> dict:
    """
    Extract information from a `<Docstring ...>...</Docstring>` block.

    Metadata (name, anchor, source, signature) comes from the component props, the
    markdown-bearing sections (parameters, returns, ...) from the component body.
    See `doc_builder.autodoc.get_signature_component_svelte` for the emitted shape.
    """
    info = {
        "name": None,
        "anchor": None,
        "source": None,
        "parameters": None,
        "paramsdesc": None,
        "paramsgroups": [],
        "rettype": None,
        "retdesc": None,
        "yieldtype": None,
        "yielddesc": None,
        "raisederrors": None,
        "raises": None,
        "is_getset_descriptor": False,
    }

    open_tag = re.match(r"<Docstring\s(?P<props>[^\n]*)>", docstring_block)
    props = open_tag.group("props") if open_tag else ""

    name = _extract_svelte_prop(props, "name")
    if name:
        # Remove "class " or "def " prefix if present
        info["name"] = re.sub(r"^(class|def)\s+", "", name.strip())

    anchor = _extract_svelte_prop(props, "anchor")
    # `anchor` is stringified python-side, so a missing anchor arrives as `"None"`.
    if anchor and anchor != "None":
        info["anchor"] = anchor.strip()

    source = _extract_svelte_prop(props, "source")
    if source:
        info["source"] = source.strip()

    parameters = _extract_svelte_prop(props, "parameters")
    if isinstance(parameters, list):
        info["parameters"] = parameters

    info["is_getset_descriptor"] = bool(_extract_svelte_prop(props, "isGetSetDescriptor"))

    for key, tag in (
        ("paramsdesc", "paramsdesc"),
        ("rettype", "rettype"),
        ("retdesc", "retdesc"),
        ("yieldtype", "yieldtype"),
        ("yielddesc", "yielddesc"),
        ("raisederrors", "raisederrors"),
        ("raises", "raises"),
    ):
        info[key] = _extract_section(docstring_block, tag)

    # Extra parameter groups, e.g. transformers' "Parameters for sequence generation".
    for group in re.findall(r"<paramsgroup>(.*?)</paramsgroup>", docstring_block, re.DOTALL):
        info["paramsgroups"].append(
            {
                "title": _extract_section(group, "paramsgrouptitle"),
                "desc": _extract_section(group, "paramsgroupdesc"),
            }
        )

    return info


def format_parameters(paramsdesc: str) -> str:
    """
    Format parameter descriptions by:
    - Removing bullets (-)
    - Removing bold formatting (**)
    - Changing -- to :
    - Adding blank lines between parameters
    """
    lines = paramsdesc.split("\n")
    formatted_params = []
    current_param = []

    for line in lines:
        # Check if this is a new parameter line (starts with "- **")
        if re.match(r"^\s*-\s+\*\*", line):
            # Save the previous parameter if exists
            if current_param:
                param_text = " ".join(current_param)
                # Remove - and ** formatting
                param_text = re.sub(r"^\s*-\s+\*\*([^*]+)\*\*", r"\1", param_text)
                # Change -- to :
                param_text = re.sub(r"\s+--\s+", " : ", param_text, count=1)
                formatted_params.append(param_text)
                formatted_params.append("")  # Add blank line between parameters
                current_param = []

            # Start new parameter
            current_param.append(line)
        elif current_param:
            # Continuation of current parameter description
            current_param.append(line.strip())

    # Don't forget the last parameter
    if current_param:
        param_text = " ".join(current_param)
        param_text = re.sub(r"^\s*-\s+\*\*([^*]+)\*\*", r"\1", param_text)
        param_text = re.sub(r"\s+--\s+", " : ", param_text, count=1)
        formatted_params.append(param_text)

    return "\n".join(formatted_params)


def format_call_signature(name: str, parameters) -> str:
    """
    Render the `parameters` prop (a list of `{"name": ..., "val": ...}`) as a call
    signature, e.g. ``HfApi.merge_pull_request(discussion_num: int, token = None)``.
    """
    args = ", ".join(f"{param.get('name', '')}{param.get('val', '')}".strip() for param in parameters)
    return f"{name}({args})"


def format_type(value: str) -> str:
    """
    Wrap a return/yield/raise type in backticks, unless it already carries markup
    (a resolved `[Name](url)` doc link, inline code, ...) that backticks would break.
    """
    return value if re.search(r"[`\[\]<>]", value) else f"`{value}`"


def process_docstring_block(docstring_block: str) -> str:
    """
    Process a docstring block by:
    1. Extracting the class/function name and relevant info
    2. Stripping all HTML tags
    3. Converting to clean markdown with level 4 header
    """
    # Extract structured information from the docstring
    info = extract_docstring_info(docstring_block)

    # Build the cleaned markdown
    parts = []

    # Add the name as level 4 header with anchor
    if info["name"]:
        if info["anchor"]:
            parts.append(f"#### {info['name']}[[{info['anchor']}]]")
        else:
            parts.append(f"#### {info['name']}")
        parts.append("")

        # Add the call signature (properties are not callable, so they have none)
        if info["parameters"] is not None and not info["is_getset_descriptor"]:
            parts.append("```python")
            parts.append(format_call_signature(info["name"], info["parameters"]))
            parts.append("```")
            parts.append("")

    # Add source link if available
    if info["source"]:
        # Strip any HTML from source
        source_clean = strip_html_tags(info["source"])
        parts.append(f"[Source]({source_clean})")
        parts.append("")

    # Add parameters description
    if info["paramsdesc"]:
        parts.append("**Parameters:**")
        parts.append("")
        # Format parameters: remove bullets and bold, change -- to :, add blank lines
        formatted_params = format_parameters(info["paramsdesc"])
        parts.append(formatted_params)
        parts.append("")

    # Add the extra parameter groups, if any
    for group in info["paramsgroups"]:
        if not group["desc"]:
            continue
        parts.append(f"**{group['title'] or 'Parameters'}:**")
        parts.append("")
        parts.append(format_parameters(group["desc"]))
        parts.append("")

    # Add the returns / yields / raises sections
    for type_key, desc_key, label in (
        ("rettype", "retdesc", "Returns"),
        ("yieldtype", "yielddesc", "Yields"),
        ("raisederrors", "raises", "Raises"),
    ):
        if not info[type_key] and not info[desc_key]:
            continue
        header = f"**{label}:**"
        if info[type_key]:
            header += f" {format_type(info[type_key])}"
        parts.append(header)
        parts.append("")
        if info[desc_key]:
            parts.append(info[desc_key])
            parts.append("")

    result = "\n".join(parts)

    # Clean up excessive newlines
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def strip_remaining_html(content: str) -> str:
    """
    Strip remaining HTML tags while preserving markdown structure.
    Handles tags like <Tip>, <ExampleCodeBlock>, etc.

    Fenced code blocks and inline code are preserved verbatim so literal
    angle-bracketed content (e.g. ``<YOUR_TOKEN>`` placeholders, or code
    such as ``if idx < n:``) survives the cleanup.
    """
    # Stash code blocks before any HTML stripping so brackets inside code are untouched.
    code_segments: list[str] = []

    def stash(match: re.Match) -> str:
        code_segments.append(match.group(0))
        return f"\x00DOCBUILDER_CODE_{len(code_segments) - 1}\x00"

    # Fenced code blocks (```...```) — match across newlines.
    content = re.sub(r"```.*?```", stash, content, flags=re.DOTALL)
    # Inline code (`...`) — single line only.
    content = re.sub(r"`[^`\n]+`", stash, content)

    # Remove HTML comments, but preserve special flags like <!-- WRAP CODE BLOCKS --> and <!-- STRETCH TABLES -->
    content = re.sub(r"<!--(?!\s*(WRAP CODE BLOCKS|STRETCH TABLES)\s*-->).*?-->", "", content, flags=re.DOTALL)

    # Remove common component tags while preserving their content
    # (Tip, TipEnd, ExampleCodeBlock, Tabs, Tab, etc.)
    tags_to_remove = [
        "Tip",
        "TipEnd",
        "ExampleCodeBlock",
        "Tabs",
        "Tab",
        "div",
        "span",
        "anchor",
    ]

    for tag in tags_to_remove:
        # Remove opening tags with any attributes
        content = re.sub(rf"<{tag}\b[^>]*>", "", content, flags=re.IGNORECASE)
        # Remove closing tags
        content = re.sub(rf"</{tag}>", "", content, flags=re.IGNORECASE)

    # Generic HTML-tag cleanup. Require the character after `<` to look like the start
    # of a tag (letter, `/`, or `!`) and forbid newlines inside the match so a stray
    # `<` in prose can't swallow content up to the next `>` further down the page.
    # Only HTML tags and (PascalCase) components are markup: `<tags>` or `<YOUR_TOKEN>` in prose are kept.
    def strip_tag(match):
        name = match.group(1)
        is_component = name and name[0].isupper() and not name.isupper()
        if name and name.lower() not in _HTML_TAGS and not is_component:
            return match.group(0)
        return ""

    content = re.sub(r"<(?:!|/?([a-zA-Z][\w.:-]*))[^>\n]*>", strip_tag, content)

    # Restore protected code segments.
    if code_segments:
        content = re.sub(
            r"\x00DOCBUILDER_CODE_(\d+)\x00",
            lambda m: code_segments[int(m.group(1))],
            content,
        )

    # Clean up multiple consecutive blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content


def strip_html_from_markdown(content: str) -> str:
    """
    Strip HTML from markdown content.

    Handles:
    - `<Docstring ...>...</Docstring>` components emitted by autodoc, which become a
      level-4 heading with the signature, then the `**Parameters:**`/`**Returns:**`
      sections. The object description follows the component in the source, so it
      keeps its place right after those (same order as the rendered HTML page).
    - Other HTML tags throughout the document
    """
    result = content

    # The opening tag's attribute values are single-line JSON (see
    # `get_signature_component_svelte`), so it ends at the last `>` on its own line.
    docstring_pattern = r"<Docstring\s[^\n]*>\n.*?</Docstring>"

    def replace_docstring(match):
        block = match.group(0)
        # Trailing newline: the object description directly follows the component (with a
        # single newline in between), and must not end up glued to the last section.
        return process_docstring_block(block) + "\n"

    result = re.sub(docstring_pattern, replace_docstring, result, flags=re.DOTALL)

    # Strip remaining HTML tags (like <Tip>, </Tip>, <ExampleCodeBlock>, etc.)
    # But preserve markdown code blocks
    result = strip_remaining_html(result)

    return result


_re_fence = re.compile(r"^\s*(`{3,}|~{3,})")
_re_inline_code = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)")


def update_fence(line, fence):
    """
    Tracks fenced code blocks line by line: returns the fence that is open after `line`, given the one open before it
    (`None` outside code). A block only closes on a fence of the same character that is at least as long, so a
    block opened with four backticks can contain three-backtick fences.
    """
    match = _re_fence.match(line)
    if match is None:
        return fence
    marker = match.group(1)
    if fence is None:
        return marker
    if marker[0] == fence[0] and len(marker) >= len(fence) and line.strip() == marker:
        return None
    return fence


def protect_code(text, inline=False, keep_block=None):
    """
    Swaps the code out of `text` for placeholders, so Markdown transforms (links, images, includes) leave code examples
    alone. Placeholders keep the line count, so line numbers in warnings stay right.

    Args:
        text (`str`): Markdown text.
        inline (`bool`, *optional*, defaults to `False`): Also protect inline code spans outside code blocks.
        keep_block (`Callable[[str], bool]`, *optional*):
            Called with the opening line of each top-level code block; blocks it returns `True` for stay in place.

    Returns:
        `Tuple[str, Callable[[str], str]]`: the protected text, and a function that puts the code back.
    """
    saved = []

    def stash(code):
        saved.append(code)
        token = f"\x00code{len(saved) - 1}\x00"
        return token + "\n" * code.count("\n")

    out = []
    block = []
    fence = None
    kept = False
    for line in text.split("\n"):
        if fence is not None:
            fence = update_fence(line, fence)
            if kept:
                out.append(line)
            else:
                block.append(line)
                if fence is None:
                    out.append(stash("\n".join(block)))
            continue
        fence = update_fence(line, None)
        if fence is not None:
            kept = keep_block is not None and keep_block(line)
            if kept:
                out.append(line)
            else:
                block = [line]
            continue
        out.append(_re_inline_code.sub(lambda m: stash(m.group(0)), line) if inline else line)
    if fence is not None and not kept:
        # an unclosed block runs to the end of the text
        out.append(stash("\n".join(block)))
    protected = "\n".join(out)

    def restore(text):
        for idx in reversed(range(len(saved))):
            code = saved[idx]
            text = text.replace(f"\x00code{idx}\x00" + "\n" * code.count("\n"), code, 1)
        return text

    return protected, restore
