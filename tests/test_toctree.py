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

from pathlib import Path

import pytest
import yaml

from doc_builder.toctree import TocPage, TocTreeError, load_toctree, parse_toctree

FIXTURE_SOURCE = Path(__file__).parent.parent / "docs" / "fixtures" / "source"


def entry(local, title=None, **kwargs):
    return {"local": local, "title": title or local, **kwargs}


def test_parse_fixture_toctree():
    toctree = load_toctree(FIXTURE_SOURCE)
    assert toctree.pages() == [
        TocPage("guide", "index", "Introduction"),
        TocPage("guide", "quickstart", "Quickstart"),
        TocPage("reference", "api/utils", "Utilities"),
    ]
    assert toctree.page_map() == {"index": "guide", "quickstart": "guide", "api/utils": "reference"}
    assert toctree.section_index("guide") == TocPage("guide", "index", "Introduction")
    assert toctree.section_index("reference") is None
    assert toctree.first_page("reference") == TocPage("reference", "api/utils", "Utilities")


def test_nested_entries_and_urls():
    toctree = parse_toctree(
        {
            "guide": [
                {
                    "title": "Tutorials",
                    "isExpanded": False,
                    "sections": [entry("tutorials/index", "Overview"), {"title": "Deep", "sections": [entry("deep")]}],
                }
            ],
            "reference": [entry("api/index", "API"), entry("index", "Reference")],
        }
    )
    assert [page.local for page in toctree.pages()] == ["tutorials/index", "deep", "api/index", "index"]
    # `tutorials/index` maps to `guide/tutorials`, not to the section root
    assert toctree.section_index("guide") is None
    assert toctree.section_index("reference") == TocPage("reference", "index", "Reference")
    assert toctree.with_urls("p", "v1") == {
        "guide": [
            {
                "title": "Tutorials",
                "isExpanded": False,
                "sections": [
                    {"title": "Overview", "local": "tutorials/index", "url": "/p/v1/guide/tutorials/"},
                    {"title": "Deep", "sections": [{"title": "deep", "local": "deep", "url": "/p/v1/guide/deep/"}]},
                ],
            }
        ],
        "reference": [
            {"title": "API", "local": "api/index", "url": "/p/v1/reference/api/"},
            {"title": "Reference", "local": "index", "url": "/p/v1/reference/"},
        ],
    }


def test_reference_is_optional():
    toctree = parse_toctree({"guide": [entry("index")]})
    assert toctree.page_map() == {"index": "guide"}
    assert toctree.with_urls("p", "main")["reference"] == []


@pytest.mark.parametrize(
    "toc, message",
    [
        ([entry("index")], "old list format"),
        ("guide", "must be a mapping"),
        ({"reference": [entry("api")]}, "`guide` section is missing"),
        ({"guide": [entry("index")], "api": []}, "unknown top-level key"),
        ({"guide": {"local": "index"}}, "`guide` must be a list"),
        ({"guide": [{"local": "index"}]}, "needs a non-empty `title`"),
        ({"guide": [{"title": "Empty"}]}, "needs a `local` or `sections`"),
        ({"guide": [entry("index.md")]}, "without extension"),
        ({"guide": [entry("/index")]}, "relative to the docs folder"),
        ({"guide": [entry("index", newlocal="home")]}, "`newlocal`, which is no longer supported"),
        ({"guide": [entry("index", local_fw={"pt": "a"})]}, "`local_fw`, which is no longer supported"),
        ({"guide": [entry("index", quiz=1)]}, "`quiz`, which is no longer supported"),
        ({"guide": [entry("index", draft=True)]}, "unknown key(s): `draft`"),
        ({"guide": [entry("index"), entry("index")]}, "`index` appears more than once (in `guide` and `guide`)"),
        ({"guide": [entry("index")], "reference": [entry("index")]}, "(in `guide` and `reference`)"),
        ({"guide": [entry("foo"), entry("foo/index")]}, "both `foo` and `foo/index` exist in `guide`"),
        ({"guide": [entry("index")], "reference": [entry("api"), entry("api/index")]}, "both `api` and `api/index`"),
    ],
)
def test_invalid_toctrees(toc, message):
    with pytest.raises(TocTreeError) as excinfo:
        parse_toctree(toc)
    assert message in str(excinfo.value)


def test_errors_are_collected(tmp_path):
    (tmp_path / "_toctree.yml").write_text(
        yaml.safe_dump({"guide": [{"local": "a"}, entry("b", newlocal="c")]}), encoding="utf-8"
    )
    with pytest.raises(TocTreeError) as excinfo:
        load_toctree(tmp_path)
    assert "`guide[0]` needs a non-empty `title`" in str(excinfo.value)
    assert "`guide[1]` uses `newlocal`" in str(excinfo.value)


def test_missing_toctree(tmp_path):
    with pytest.raises(TocTreeError, match="No `_toctree.yml`"):
        load_toctree(tmp_path)


def test_index_conflicts_are_per_section():
    # `guide/models/` and `reference/models/` are different URLs
    toctree = parse_toctree({"guide": [entry("models")], "reference": [entry("models/index")]})
    assert [page.local for page in toctree.pages()] == ["models", "models/index"]
