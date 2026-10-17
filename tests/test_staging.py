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
Golden test of the Python -> kit handoff (contract C5): building and staging `docs/fixtures/source` must produce
exactly `docs/fixtures/handoff`.

The fixture documents an imaginary `sample` package with `[[autodoc]] utils.get_doc_config`; a stand-in package lives
in `tests/fixtures/sample_pkg`, so the autodoc page is compared too (not just the structure).
"""

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from doc_builder import build_doc
from doc_builder.commands.build import stage_kit_routes
from doc_builder.staging import Site, get_docs_path_in_repo, stage_site
from doc_builder.utils import get_project_info, read_doc_config

REPO_ROOT = Path(__file__).parent.parent
FIXTURES = REPO_ROOT / "docs" / "fixtures"
SAMPLE_PKG = Path(__file__).parent / "fixtures" / "sample_pkg"
SOURCE_REF = "0123456789abcdef0123456789abcdef01234567"


def normalize(text):
    """Whitespace-insensitive comparison: no trailing spaces, single blank lines, no leading/trailing blank lines."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def all_files(folder):
    return sorted(p.relative_to(folder).as_posix() for p in Path(folder).rglob("*") if p.is_file())


@pytest.fixture
def sample_package(monkeypatch):
    monkeypatch.syspath_prepend(str(SAMPLE_PKG))
    yield
    for name in [name for name in sys.modules if name == "sample" or name.startswith("sample.")]:
        del sys.modules[name]


@pytest.fixture
def fixture_build(tmp_path, sample_package):
    """Builds the fixture docs as if they were the `docs/` folder of the `cerulean-works/sample` repo."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    docs = repo / "docs"
    shutil.copytree(FIXTURES / "source", docs)
    mdx_dir = tmp_path / "mdx"
    read_doc_config(docs)
    info = get_project_info("sample")
    doc_build = build_doc(
        "sample",
        docs,
        mdx_dir,
        version="v0.1.0",
        source_ref=SOURCE_REF,
        is_python_module=True,
        repo=info["repo"],
    )
    site = Site(
        project="sample",
        version="v0.1.0",
        title=info["title"],
        description=info["description"],
        repo=info["repo"],
        source_ref=SOURCE_REF,
        docs_path=get_docs_path_in_repo(docs),
    )
    yield docs, mdx_dir, doc_build, site
    read_doc_config(tmp_path)


def test_stage_matches_handoff_fixture(tmp_path, fixture_build):
    docs, mdx_dir, doc_build, site = fixture_build
    staged = tmp_path / "staged"
    stage_site(staged, mdx_dir, docs, doc_build.toctree, site)

    expected = FIXTURES / "handoff"
    assert all_files(staged) == all_files(expected)
    for relative in all_files(expected):
        expected_file, staged_file = expected / relative, staged / relative
        if relative.endswith(".json"):
            assert json.loads(staged_file.read_text()) == json.loads(expected_file.read_text()), relative
        elif relative.endswith(".png"):
            assert staged_file.read_bytes() == expected_file.read_bytes(), relative
        else:
            assert normalize(staged_file.read_text()) == normalize(expected_file.read_text()), relative


def test_markdown_exports(tmp_path, fixture_build):
    docs, mdx_dir, doc_build, site = fixture_build
    exports = dict(stage_site(tmp_path / "staged", mdx_dir, docs, doc_build.toctree, site))

    # C1 paths, in toctree order
    assert list(exports) == ["guide.md", "guide/quickstart.md", "reference/api/utils.md"]
    for markdown in exports.values():
        assert "HF_DOC_BODY" not in markdown
        assert "<script" not in markdown
        assert "<Docstring" not in markdown
        assert "<div" not in markdown
    assert exports["guide.md"].startswith("# Introduction\n")
    assert (
        "[utils.get_doc_config()](/sample/v0.1.0/reference/api/utils/#sample.utils.get_doc_config)"
        in exports["guide.md"]
    )
    assert "Braces like {x} and <tags> in text are escaped." in exports["guide/quickstart.md"]
    assert "![A single pixel](/sample/v0.1.0/imgs/pixel.png)" in exports["guide/quickstart.md"]
    assert "#### sample.utils.get_doc_config[[sample.utils.get_doc_config]]" in exports["reference/api/utils.md"]
    assert "Returns the `doc_config` if it has been loaded." in exports["reference/api/utils.md"]


def test_stage_kit_routes(tmp_path, fixture_build):
    docs, mdx_dir, doc_build, site = fixture_build
    kit = tmp_path / "kit_src"
    (kit / "src" / "routes").mkdir(parents=True)
    (kit / "src" / "routes" / "+layout.svelte").write_text("<slot />", encoding="utf-8")
    (kit / "node_modules" / "dep").mkdir(parents=True)
    (kit / "build").mkdir()
    (kit / "package.json").write_text("{}", encoding="utf-8")

    work = tmp_path / "work"
    work.mkdir()
    kit_dir, exports = stage_kit_routes(kit, work, mdx_dir, docs, doc_build.toctree, site)

    assert kit_dir == work / "kit"
    assert (kit_dir / "package.json").is_file()
    assert (kit_dir / "src" / "routes" / "+layout.svelte").is_file()
    assert not (kit_dir / "node_modules").exists()
    assert not (kit_dir / "build").exists()
    assert (kit_dir / "src" / "routes" / "guide" / "quickstart" / "+page.svelte").is_file()
    assert (kit_dir / "src" / "lib" / "generated" / "site.json").is_file()
    assert (kit_dir / "static" / "imgs" / "pixel.png").is_file()
    assert [path for path, _ in exports] == ["guide.md", "guide/quickstart.md", "reference/api/utils.md"]
    # the kit itself is never touched
    assert all_files(kit) == ["package.json", "src/routes/+layout.svelte"]


def test_stage_redirects_and_index_rules(tmp_path):
    docs = tmp_path / "docs"
    (docs / "tutorials").mkdir(parents=True)
    (docs / "api").mkdir()
    (docs / "_toctree.yml").write_text(
        "guide:\n"
        "  - title: Tutorials\n"
        "    sections:\n"
        "      - local: tutorials/index\n"
        "        title: Overview\n"
        "      - local: tutorials/first\n"
        "        title: First\n"
        "reference:\n"
        "  - local: api/index\n"
        "    title: API\n"
        "  - local: index\n"
        "    title: Reference\n",
        encoding="utf-8",
    )
    for name in ("tutorials/index.md", "tutorials/first.md", "api/index.mdx", "index.rst"):
        (docs / name).write_text("# Title\n", encoding="utf-8")
    mdx_dir = tmp_path / "mdx"
    doc_build = build_doc("proj", docs, mdx_dir, version="pr_7")
    site = Site("proj", "pr_7", "Proj", "", "acme/proj", "abc", docs_path="")
    staged = tmp_path / "staged"
    exports = stage_site(staged, mdx_dir, docs, doc_build.toctree, site)
    read_doc_config(tmp_path)

    assert all_files(staged / "src" / "routes") == [
        "guide/+page.svelte",
        "guide/+page.ts",
        "guide/tutorials/+page.svelte",
        "guide/tutorials/+page.ts",
        "guide/tutorials/first/+page.svelte",
        "guide/tutorials/first/+page.ts",
        "reference/+page.svelte",
        "reference/+page.ts",
        "reference/api/+page.svelte",
        "reference/api/+page.ts",
    ]
    # `guide` has no `index` page: its root redirects to the first entry
    redirect = (staged / "src" / "routes" / "guide" / "+page.ts").read_text()
    assert "redirect(308, `${base}/guide/tutorials/`);" in redirect
    assert "Docstring" not in (staged / "src" / "routes" / "guide" / "+page.svelte").read_text()
    # `reference` has one, from an `.rst` source at the docs root
    page_ts = (staged / "src" / "routes" / "reference" / "+page.ts").read_text()
    assert 'section: "reference",' in page_ts
    assert 'title: "Reference",' in page_ts
    assert 'editUrl: "https://github.com/acme/proj/blob/abc/index.rst",' in page_ts
    assert 'mdUrl: "/proj/pr_7/reference.md",' in page_ts
    assert (
        'mdUrl: "/proj/pr_7/reference/api.md",'
        in (staged / "src" / "routes" / "reference" / "api" / "+page.ts").read_text()
    )
    assert [path for path, _ in exports] == [
        "guide/tutorials.md",
        "guide/tutorials/first.md",
        "reference/api.md",
        "reference.md",
    ]
    site_json = json.loads((staged / "src" / "lib" / "generated" / "site.json").read_text())
    assert site_json["version"] == "pr_7"
    assert site_json["toctree"]["guide"][0]["sections"][0]["url"] == "/proj/pr_7/guide/tutorials/"


def test_get_docs_path_in_repo(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "docs" / "source").mkdir(parents=True)
    assert get_docs_path_in_repo(tmp_path / "docs" / "source") == "docs/source"
    assert get_docs_path_in_repo(tmp_path) == ""


def test_kit_copy_skips_leftover_pages(tmp_path):
    from doc_builder.commands.build import KIT_COPY_IGNORE

    kit = tmp_path / "kit"
    for rel in [
        "src/routes/+layout.svelte",
        "src/routes/+error.svelte",
        "src/routes/guide/+page.svelte",
        "static/favicon.png",
        "static/imgs/pixel.png",
        "src/lib/Tip.svelte",
        "node_modules/x/index.js",
    ]:
        (kit / rel).parent.mkdir(parents=True, exist_ok=True)
        (kit / rel).write_text("")

    shutil.copytree(kit, tmp_path / "copy", ignore=KIT_COPY_IGNORE)

    copied = sorted(p.relative_to(tmp_path / "copy").as_posix() for p in (tmp_path / "copy").rglob("*") if p.is_file())
    assert copied == [
        "src/lib/Tip.svelte",
        "src/routes/+error.svelte",
        "src/routes/+layout.svelte",
        "static/favicon.png",
    ]


@pytest.mark.parametrize(
    "project,version,ok",
    [
        ("flock", "main", True),
        ("flock", "v1.0.0+cpu", True),
        ("flock", "pr_12", True),
        ("my-lib_2", "v2.0.0rc1", True),
        ("my.lib", "main", False),  # the Worker never serves a project with a dot
        ("flock", "latest", False),  # reserved alias for the default version
        ("flock", "../x", False),
    ],
)
def test_check_names(project, version, ok):
    from doc_builder.commands.build import check_names

    if ok:
        check_names(project, version)
    else:
        with pytest.raises(ValueError):
            check_names(project, version)


@pytest.mark.parametrize(
    "available,expected",
    [
        ({"pnpm", "corepack"}, ["/bin/pnpm"]),
        ({"corepack"}, ["/bin/corepack", "pnpm"]),
        (set(), None),
    ],
)
def test_pnpm_command(monkeypatch, available, expected):
    from doc_builder.commands import build

    monkeypatch.setattr(build.shutil, "which", lambda name: f"/bin/{name}" if name in available else None)
    if expected is None:
        with pytest.raises(OSError, match="requires pnpm"):
            build.pnpm_command()
    else:
        assert build.pnpm_command() == expected
