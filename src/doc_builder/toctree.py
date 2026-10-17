# Copyright 2026 The HuggingFace Team and cerulean-works. All rights reserved.
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

"""
The `_toctree.yml` format (contract C4): a mapping with a `guide` and a `reference` key, each holding a list of
`{title, local?, sections?, isExpanded?}` entries.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from .utils import doc_url, page_route

SECTIONS = ("guide", "reference")
ENTRY_KEYS = {"title", "local", "sections", "isExpanded"}
UNSUPPORTED_KEYS = {"newlocal", "local_fw", "quiz"}


class TocTreeError(ValueError):
    pass


@dataclass(frozen=True)
class TocPage:
    section: str
    local: str
    title: str


@dataclass
class TocTree:
    """A validated toctree: `sections` maps each section name to its (nested) entries."""

    sections: dict

    def pages(self):
        """All pages, in toctree order (guide first, depth-first)."""
        pages = []
        for section in SECTIONS:
            for entry in _walk(self.sections[section]):
                if "local" in entry:
                    pages.append(TocPage(section, entry["local"], entry["title"]))
        return pages

    def page_map(self):
        """Maps each page `local` to its section."""
        return {page.local: page.section for page in self.pages()}

    def section_index(self, section):
        """The page that is the root of `section` (`index` or `<dir>/index` mapping to the section), if any."""
        for page in self.pages():
            if page.section == section and page_route(section, page.local) == section:
                return page
        return None

    def first_page(self, section):
        for page in self.pages():
            if page.section == section:
                return page
        return None

    def with_urls(self, project, version):
        """A JSON-ready copy of the sections where every entry with a `local` also has its resolved `url`."""

        def resolve(entries, section):
            resolved = []
            for entry in entries:
                new_entry = {"title": entry["title"]}
                if "local" in entry:
                    new_entry["local"] = entry["local"]
                    new_entry["url"] = doc_url(project, version, section, entry["local"])
                if "isExpanded" in entry:
                    new_entry["isExpanded"] = entry["isExpanded"]
                if "sections" in entry:
                    new_entry["sections"] = resolve(entry["sections"], section)
                resolved.append(new_entry)
            return resolved

        return {section: resolve(self.sections[section], section) for section in SECTIONS}


def _walk(entries):
    for entry in entries:
        yield entry
        yield from _walk(entry.get("sections", []))


def _validate_entries(entries, where, errors):
    if not isinstance(entries, list):
        errors.append(f"- `{where}` must be a list of entries.")
        return
    for idx, entry in enumerate(entries):
        location = f"{where}[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"- `{location}` must be a mapping with at least a `title`.")
            continue
        unsupported = sorted(UNSUPPORTED_KEYS & entry.keys())
        if unsupported:
            errors.append(
                f"- `{location}` uses {', '.join(f'`{k}`' for k in unsupported)}, which is no longer supported."
            )
        unknown = sorted(entry.keys() - ENTRY_KEYS - UNSUPPORTED_KEYS)
        if unknown:
            errors.append(f"- `{location}` has unknown key(s): {', '.join(f'`{k}`' for k in unknown)}.")
        if not isinstance(entry.get("title"), str) or not entry["title"].strip():
            errors.append(f"- `{location}` needs a non-empty `title`.")
        if "local" in entry:
            local = entry["local"]
            if not isinstance(local, str) or not local.strip():
                errors.append(f"- `{location}`: `local` must be a non-empty string.")
            elif local.startswith("/") or local.endswith("/") or Path(local).suffix in (".md", ".mdx", ".rst"):
                errors.append(
                    f"- `{location}`: `local` ({local}) must be a path relative to the docs folder, without extension."
                )
        if "sections" in entry:
            _validate_entries(entry["sections"], f"{location}.sections", errors)
        elif "local" not in entry:
            errors.append(f"- `{location}` needs a `local` or `sections`.")


def parse_toctree(toc, source="_toctree.yml"):
    """
    Validates a loaded `_toctree.yml` and returns a `TocTree`. Raises `TocTreeError` listing every problem found.
    """
    if isinstance(toc, list):
        raise TocTreeError(
            f"{source} uses the old list format. It must be a mapping with a `guide` and a `reference` key, e.g.\n"
            "guide:\n  - title: Get started\n    sections:\n      - local: index\n        title: Introduction\n"
            "reference:\n  - title: API\n    sections:\n      - local: api/main\n        title: Main classes"
        )
    if not isinstance(toc, dict):
        raise TocTreeError(f"{source} must be a mapping with a `guide` and a `reference` key.")

    errors = []
    unknown = sorted(set(toc) - set(SECTIONS))
    if unknown:
        errors.append(
            f"- unknown top-level key(s): {', '.join(f'`{k}`' for k in unknown)} (expected `guide`, `reference`)."
        )
    if not toc.get("guide"):
        errors.append("- the `guide` section is missing or empty.")
    sections = {section: toc.get(section) or [] for section in SECTIONS}
    for section in SECTIONS:
        _validate_entries(sections[section], section, errors)
    if errors:
        raise TocTreeError(f"{source} is invalid:\n" + "\n".join(errors))

    tree = TocTree(sections)
    seen = {}
    for page in tree.pages():
        if page.local in seen:
            errors.append(
                f"- `{page.local}` appears more than once (in `{seen[page.local]}` and `{page.section}`); every page "
                "must appear exactly once."
            )
        seen.setdefault(page.local, page.section)
    errors.extend(index_conflicts(tree.pages()))
    if errors:
        raise TocTreeError(f"{source} is invalid:\n" + "\n".join(errors))
    return tree


def index_conflicts(pages):
    """Errors for every `foo` listed in the same section as `foo/index` (both would be served at the same URL)."""
    listed = {(page.section, page.local) for page in pages}
    return [
        f"- both `{local[: -len('/index')]}` and `{local}` exist in `{section}`; they would have the same URL."
        for section, local in sorted(listed)
        if local.endswith("/index") and (section, local[: -len("/index")]) in listed
    ]


def load_toctree(doc_folder):
    toc_file = Path(doc_folder) / "_toctree.yml"
    if not toc_file.is_file():
        raise TocTreeError(f"No `_toctree.yml` found in {doc_folder}.")
    with open(toc_file, encoding="utf-8") as f:
        toc = yaml.safe_load(f.read())
    return parse_toctree(toc, source=str(toc_file))
