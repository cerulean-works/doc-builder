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


import json
import os
import posixpath
import re
import sys

from .convert_rst_to_mdx import parse_rst_docstring, remove_indent
from .utils import protect_code, resolve_page_url

_re_doctest_flags = re.compile(r"^(>>>.*\S)(\s+)# doctest:\s+\+[A-Z_]+\s*$", flags=re.MULTILINE)

# Components every page imports (contract C5). The kit must provide each of them in `$lib`.
PAGE_COMPONENTS = (
    "Tip",
    "Added",
    "Changed",
    "Deprecated",
    "CodeBlock",
    "ExampleCodeBlock",
    "Docstring",
    "Heading",
    "MermaidChart",
    "Youtube",
    "Tabs",
    "Tab",
)
PAGE_SCRIPT = (
    '<script lang="ts">\n'
    + "".join(f'import {name} from "$lib/{name}.svelte";\n' for name in PAGE_COMPONENTS)
    + "</script>"
)


def wrap_page_body(body):
    """
    Wraps a page body into the `+page.svelte` shape of contract C5: the component imports, then the body between the
    `HF_DOC_BODY_START`/`HF_DOC_BODY_END` markers (the kit escapes `{` and `<` between them).
    """
    return f"{PAGE_SCRIPT}\n\nHF_DOC_BODY_START\n\n{body.strip()}\n\nHF_DOC_BODY_END\n"


def convert_md_to_mdx(md_text, page_info):
    """
    Convert a document written in md to mdx.
    """
    return wrap_page_body(process_md(md_text, page_info))


_re_uri_scheme = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_re_legacy_img_link = re.compile(r"(src=\"|\()/imgs/")
_re_md_img = re.compile(r"(!\[[^\]]*\]\()([^)\s]+)")
_re_html_img_src = re.compile(r"(<img\b[^>]*?\bsrc=([\"']))(.*?)\2", re.I)


def _is_relative_url(url):
    return not (url.startswith(("/", "#", "{", "<", "?")) or _re_uri_scheme.match(url))


def _resolve_relative_path(url, page_info):
    """
    Resolves `url`, relative to the current page's source file, to a path relative to the docs folder. Returns
    `None` if it points outside of the docs folder.
    """
    target = posixpath.normpath(posixpath.join(page_info.get("page_dir", ""), url))
    if target == ".":
        return ""
    return None if target == ".." or target.startswith("../") else target


def page_base_url(page_info):
    """The `/<project>/<version>/` base path that every link and image starts with (contract C5)."""
    return f"/{page_info['package_name']}/{page_info.get('version', 'main')}/"


def convert_img_links(text, page_info):
    """
    Makes image sources absolute: `/<project>/<version>/<path in the docs folder>`. Relative sources are resolved
    against the page's folder, and the legacy `/imgs/...` form against the docs folder.
    """
    if "package_name" not in page_info:
        raise ValueError("`page_info` must contain at least the package_name.")
    base = page_base_url(page_info)

    def absolute(url):
        if not _is_relative_url(url):
            return url
        target = _resolve_relative_path(url, page_info)
        return f"{base}{target}" if target else url

    text = _re_legacy_img_link.sub(rf"\1{base}imgs/", text)
    text = _re_md_img.sub(lambda m: m.group(1) + absolute(m.group(2)), text)
    text = _re_html_img_src.sub(lambda m: m.group(1) + absolute(m.group(3)) + m.group(2), text)
    return text


_re_md_img_tag_alt = re.compile(r"!\[([^\]]+)\]", re.I)
_re_html_img_tag_alt = re.compile(r"<img [^>]*?alt=([\"'])([^\1]*?)\1[^>]*?>", re.I)


def escape_img_alt_description(text):
    """
    Escapes ` with ' inside <img> alt description since it causes svelte/mdsvex compiler error.
    """

    def replace_md_alt_content(match):
        alt_content = match.group(1)
        new_alt_content = alt_content.replace("`", "'")
        return match.group(0).replace(alt_content, new_alt_content)

    def replace_html_alt_content(match):
        alt_content = match.group(2)  # group(2) contains the alt text for the HTML regex
        new_alt_content = alt_content.replace("`", "'")
        return match.group(0).replace(alt_content, new_alt_content)

    # Replace markdown style image alt text
    if _re_md_img_tag_alt.search(text):
        text = _re_md_img_tag_alt.sub(replace_md_alt_content, text)

    # Replace HTML style image alt text
    if _re_html_img_tag_alt.search(text):
        text = _re_html_img_tag_alt.sub(replace_html_alt_content, text)

    return text


def fix_img_links(text, page_info):
    text = convert_img_links(text, page_info)
    text = escape_img_alt_description(text)
    return text


def clean_doctest_syntax(text):
    """
    Clean the doctest artifacts in a given content.
    """
    text = _re_doctest_flags.sub(r"\1", text)
    return text


_re_include_template = r"([ \t]*)<{include_name}>(((?!<{include_name}>).)*)<\/{include_name}>"
_re_include = re.compile(_re_include_template.format(include_name="include"), re.DOTALL)
_re_literalinclude = re.compile(_re_include_template.format(include_name="literalinclude"), re.DOTALL)


def convert_file_include_helper(match, page_info, is_code=True):
    """
    Convert an `include` or `literalinclude` regex match into markdown blocks or markdown code blocks,
    by opening a file and copying specified start-end section into markdown block.

    If `is_code` is True, the block will be rendered as a code block, otherwise it will be rendered
    as a markdown block.
    """
    include_info = json.loads(match[2].strip())
    indent = match[1]
    include_name = "literalinclude" if is_code else "include"
    file = page_info["path"].parent / include_info["path"]
    with open(file, encoding="utf-8-sig") as reader:
        lines = reader.readlines()
    include = lines  # defaults to entire file
    if "start-after" in include_info or "end-before" in include_info:
        start_after, end_before = -1, -1
        for idx, line in enumerate(lines):
            line = line.strip()
            line = re.sub(r"\W+$", "", line)
            if line.endswith(include_info["start-after"]):
                start_after = idx + 1
            if line.endswith(include_info["end-before"]):
                end_before = idx
        if start_after == -1 or end_before == -1:
            raise ValueError(f"The following '{include_name}' does NOT exist:\n{match[0]}")
        include = lines[start_after:end_before]
    include = [indent + line[include_info.get("dedent", 0) :] for line in include]
    include = "".join(include).rstrip()
    return f"""{indent}```{include_info.get("language", "")}\n{include}\n{indent}```""" if is_code else include


def convert_include(text, page_info):
    """
    Convert an `include` into markdown.
    """
    text = _re_include.sub(lambda m: convert_file_include_helper(m, page_info, is_code=False), text)
    return text


def convert_literalinclude(text, page_info):
    """
    Convert a `literalinclude` into markdown code blocks.
    """
    text = _re_literalinclude.sub(lambda m: convert_file_include_helper(m, page_info, is_code=True), text)
    return text


def convert_md_docstring_to_mdx(docstring, page_info):
    """
    Convert a docstring written in Markdown to mdx.
    """
    text = parse_rst_docstring(docstring)
    text = remove_indent(text)
    return process_md(text, page_info)


_re_markdown_link = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def strip_md_extension_from_internal_links(text):
    """
    Strip .md extensions from internal/relative links in markdown text.

    This allows both [Overview](./overview.md) and [Overview](./overview) to work.
    External links (http/https), anchor-only links (#), and absolute paths are preserved.
    """

    def _process_link(match):
        link_text, link_url = match.groups()

        if link_url.startswith(("http://", "https://", "//")):
            return match.group(0)

        if link_url.startswith("#"):
            return match.group(0)

        if link_url.startswith("/"):
            return match.group(0)

        if ".md" in link_url:
            link_url = link_url.replace(".md#", "#").replace(".md?", "?")
            if link_url.endswith(".md"):
                link_url = link_url[:-3]

        return f"[{link_text}]({link_url})"

    return _re_markdown_link.sub(_process_link, text)


_re_page_extension = re.compile(r"\.(?:mdx?|rst|html)$")


def resolve_internal_links(text, page_info):
    """
    Makes relative links absolute (contract C5): links to pages become their section-aware URL
    (`/<project>/<version>/<section>/<page>/`) and links to other files `/<project>/<version>/<path>`. Links to pages
    that are not in the toctree are left untouched. Needs `page_map` (page local -> section) in `page_info`.
    """
    if "page_map" not in page_info:
        return text

    def _process_link(match):
        link_text, link_url = match.groups()
        if not _is_relative_url(link_url) or " " in link_url.strip():
            return match.group(0)
        split = re.search(r"[#?]", link_url)
        path, rest = (link_url[: split.start()], link_url[split.start() :]) if split else (link_url, "")
        target = _resolve_relative_path(_re_page_extension.sub("", path), page_info)
        if target is None:
            return match.group(0)
        url = resolve_page_url(target, page_info)
        if url is None and posixpath.splitext(target)[1]:
            url = f"{page_base_url(page_info)}{target}"
        if url is None:
            return match.group(0)
        return f"[{link_text}]({url}{rest})"

    return _re_markdown_link.sub(_process_link, text)


_re_runnable_block = re.compile(
    r"(?P<fence>```(?:py|python))\s+runnable:(?P<label>\S+)\n(?P<code>.*?\n)```$",
    re.DOTALL | re.MULTILINE,
)
_re_runnable_fence = re.compile(r"^```(?:py|python)\s+runnable\b")
_re_bare_assert = re.compile(r"^assert(?:\s|\()")
_re_silence_bare_assert_warning = re.compile(r"#\s*(?:doc-builder:\s*)?ignore-bare-assert\b")
_re_silence_bare_assert_comment = re.compile(r"\s*#\s*(?:doc-builder:\s*)?ignore-bare-assert\b.*$")
_re_hide_directive = re.compile(r"#\s*doc-builder:\s*hide\b")


_re_pytest_decorator = re.compile(r"^#\s*pytest-decorator:")


def _should_hide_line(stripped):
    """Check if a line is marked with ``# doc-builder: hide`` or is a ``# pytest-decorator:`` directive."""
    if _re_hide_directive.search(stripped):
        return True
    if _re_pytest_decorator.match(stripped):
        return True
    return False


def _is_bare_assert(stripped):
    """Check if a line starts with a bare assert statement."""
    return _re_bare_assert.match(stripped) is not None


def _should_silence_bare_assert_warning(stripped):
    """Check if a bare assert warning should be silenced."""
    return _re_silence_bare_assert_warning.search(stripped) is not None


def _strip_bare_assert_silence_comment(line):
    """Remove bare assert silence marker comments from rendered code."""
    return _re_silence_bare_assert_comment.sub("", line).rstrip()


def _is_multiline(stripped):
    """Return True when a hidden line continues on the next line(s)."""
    paren_depth = stripped.count("(") - stripped.count(")") + stripped.count("[") - stripped.count("]")
    return paren_depth > 0 or stripped.rstrip().endswith("\\")


def _clean_code_for_doc(code, track_bare_assert=False):
    """
    Remove lines that should not appear in rendered documentation:

    * Any line (or multi-line statement) annotated with a ``# doc-builder: hide`` comment.
    * When ``# doc-builder: hide`` appears on a block opener (``for``/``if``/etc.),
      the entire indented body is removed as well.
    """
    lines = code.split("\n")
    result = []
    bare_assert_line_numbers = []
    paren_depth = 0
    skipping = False
    # When a block opener is marked # doc-builder: hide, skip all lines indented deeper.
    skip_block_indent = -1
    for line_number, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Skip body of a # doc-builder: hide block opener
        if skip_block_indent >= 0:
            if stripped == "" or indent > skip_block_indent:
                continue
            # Back to same or lesser indent — stop skipping
            skip_block_indent = -1

        if skipping:
            # Track parentheses / brackets to find end of multi-line statement
            paren_depth += stripped.count("(") - stripped.count(")") + stripped.count("[") - stripped.count("]")
            if paren_depth <= 0 and not stripped.rstrip().endswith("\\"):
                skipping = False
            continue

        if _should_hide_line(stripped):
            if _is_multiline(stripped):
                paren_depth = stripped.count("(") - stripped.count(")") + stripped.count("[") - stripped.count("]")
                skipping = True
            elif _re_block_opener.match(stripped):
                # Block opener with # doc-builder: hide - skip the entire indented body
                skip_block_indent = indent
            _remove_empty_block_opener(result, indent)
            continue

        if track_bare_assert and _is_bare_assert(stripped) and not _should_silence_bare_assert_warning(stripped):
            bare_assert_line_numbers.append(line_number)

        result.append(_strip_bare_assert_silence_comment(line))

    # Collapse runs of multiple blank lines into one
    cleaned = []
    for line in result:
        if line.strip() == "" and cleaned and cleaned[-1].strip() == "":
            continue
        cleaned.append(line)

    return "\n".join(cleaned), bare_assert_line_numbers


_re_block_opener = re.compile(r"^(for |if |while |with |elif |else\s*:)")


def _remove_empty_block_opener(result, assert_indent):
    """
    Walk backwards through *result* and remove the nearest block opener
    if the assert we're about to remove was its only body line.
    """
    # Find the last non-blank line
    idx = len(result) - 1
    while idx >= 0 and result[idx].strip() == "":
        idx -= 1
    if idx < 0:
        return

    prev = result[idx]
    prev_stripped = prev.lstrip()
    prev_indent = len(prev) - len(prev_stripped)

    # The opener must be less indented than the assert and end with ':'
    if prev_indent < assert_indent and prev_stripped.endswith(":") and _re_block_opener.match(prev_stripped):
        # Remove the opener and any blank lines between it and here
        del result[idx:]


def _to_github_annotation_value(value):
    return str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _emit_bare_assert_warning(message, page_info=None, line_number=None):
    file_path = str(page_info["path"]) if page_info is not None and "path" in page_info else None
    if os.getenv("GITHUB_ACTIONS") == "true":
        message = _to_github_annotation_value(message)
        if file_path is None:
            print(f"::warning::{message}", file=sys.stderr)
            return

        file_path = _to_github_annotation_value(file_path)
        if line_number is not None:
            print(f"::warning file={file_path},line={line_number}::{message}", file=sys.stderr)
        else:
            print(f"::warning file={file_path}::{message}", file=sys.stderr)
        return

    if file_path is None:
        print(f"Warning: {message}", file=sys.stderr)
        return

    if line_number is not None:
        print(f"Warning: {file_path}:{line_number}: {message}", file=sys.stderr)
    else:
        print(f"Warning: {file_path}: {message}", file=sys.stderr)


def _should_emit_bare_assert_warnings(page_info=None):
    return bool(page_info is not None and page_info.get("emit_warning", False))


def clean_runnable_blocks(text, page_info=None):
    """
    Process ```py runnable:<label> code blocks:
      1. Strip the runnable:<label> annotation from the fence.
      2. Remove ``# doc-builder: hide`` lines and blocks from displayed code.
      3. Optionally warn on bare ``assert`` statements when
         ``page_info["emit_warning"]`` is enabled, unless explicitly silenced
         with ``# doc-builder: ignore-bare-assert``.
    """

    def _replace(match):
        fence = match.group("fence")
        label = match.group("label")
        emit_warning = _should_emit_bare_assert_warnings(page_info)
        code, bare_assert_line_numbers = _clean_code_for_doc(match.group("code"), track_bare_assert=emit_warning)
        if emit_warning and bare_assert_line_numbers:
            first_code_line = text[: match.start("code")].count("\n") + 1
            for relative_line in bare_assert_line_numbers:
                _emit_bare_assert_warning(
                    (
                        f"Bare assert found in runnable:{label}. Add `# doc-builder: hide` to hide it from docs, "
                        "or `# doc-builder: ignore-bare-assert` to silence this warning."
                    ),
                    page_info=page_info,
                    line_number=first_code_line + relative_line - 1,
                )
        # Strip trailing blank lines inside the block
        code = code.rstrip("\n") + "\n"
        return f"{fence}\n{code}```"

    return _re_runnable_block.sub(_replace, text)


def process_md(text, page_info):
    """
    Processes markdown by:
        1. Convert include
        2. Convert literalinclude
        3. Clean doctest syntax
        4. Fix image links
        5. Strip .md extensions from internal links and make them absolute
        6. Clean runnable code blocks
    """
    # Code is shielded from the Markdown transforms, so examples of doc-builder syntax are shown as written.
    text, restore = protect_code(text)
    text = convert_include(text, page_info)
    text = convert_literalinclude(text, page_info)
    text = restore(text)
    text = clean_doctest_syntax(text)
    text, restore = protect_code(text, inline=True)
    text = fix_img_links(text, page_info)
    text = strip_md_extension_from_internal_links(text)
    text = resolve_internal_links(text, page_info)
    text = restore(text)
    # Only top-level ```py/```python fences are runnable: a runnable fence shown inside a longer fence is an example.
    text, restore = protect_code(text, keep_block=lambda line: _re_runnable_fence.match(line) is not None)
    text = clean_runnable_blocks(text, page_info=page_info)
    return restore(text)
