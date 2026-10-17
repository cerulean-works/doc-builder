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
End-to-end HTML build of doc-builder's own docs, `docs/source/` (contract C3). Needs node, pnpm and the kit, so it is deselected by default:

    uv run pytest tests/test_e2e.py -m e2e
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        shutil.which("node") is None or (shutil.which("pnpm") is None and shutil.which("corepack") is None),
        reason="needs node and pnpm",
    ),
]


def test_build_own_docs_html(tmp_path):
    subprocess.run(
        [
            sys.executable,
            "-m",
            "doc_builder.commands.doc_builder_cli",
            "build",
            "doc-builder",
            "docs/source",
            "--not_python_module",
            "--version",
            "main",
            "--build_dir",
            str(tmp_path),
            "--html",
            "--site_url",
            "https://docs.example.com",
        ],
        cwd=REPO_ROOT,
        check=True,
        timeout=1200,
    )
    out = tmp_path / "doc-builder" / "main"
    files = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}

    pages = ["guide/index.html", "guide/writing/index.html", "reference/cli/index.html"]
    exports = ["guide.md", "guide/writing.md", "reference/cli.md"]
    other = ["404.html", "llms.txt", "llms-full.txt", "_project.json", "_app/version.json"]
    for expected in pages + exports + other:
        assert expected in files, expected
    # `reference` has no index page: it is a redirect page
    assert "reference/index.html" in files
    assert any(f.startswith("_app/immutable/") for f in files)
    assert any(f.startswith("pagefind/") for f in files)
    # no Python module, no inventory; no `.html` page routes other than `index.html`
    assert "objects.inv" not in files
    assert all(
        f.endswith("/index.html") or "/" not in f or f.startswith("_app/") for f in files if f.endswith(".html")
    )

    for page in pages:
        html = (out / page).read_text(encoding="utf-8")
        assert html.lstrip().lower().startswith("<!doctype html>")
        assert "/doc-builder/main/_app/" in html
    assert "HF_DOC_BODY" not in (out / "guide" / "writing" / "index.html").read_text(encoding="utf-8")

    writing = (out / "guide" / "writing.md").read_text(encoding="utf-8")
    assert writing.startswith("# Writing pages")
    # a relative link from the Guide resolves to the Reference page of the same version
    assert "[Markdown syntax](/doc-builder/main/reference/syntax/)" in writing
    llms = (out / "llms.txt").read_text(encoding="utf-8")
    assert "https://docs.example.com/doc-builder/main/guide/writing.md" in llms
    assert json.loads((out / "_project.json").read_text(encoding="utf-8")) == {
        "name": "doc-builder",
        "title": "doc-builder",
        "description": "Builds and serves the documentation of cerulean-works projects.",
        "repo": "cerulean-works/doc-builder",
    }
