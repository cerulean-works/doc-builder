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

import tempfile
import unittest
import zlib
from pathlib import Path

from doc_builder.build_doc import (
    _re_autodoc,
    _re_list_item,
    build_doc,
    check_toc_integrity,
    convert_anchors_mapping_to_sphinx_format,
    resolve_autodoc,
)
from doc_builder.utils import read_doc_config

TOCTREE = """guide:
  - title: Get started
    sections:
      - local: index
        title: Introduction
      - local: tutorials/first
        title: First steps
reference:
  - title: API
    sections:
      - local: api/main
        title: Main classes
"""


def write_docs(folder, toctree=TOCTREE, files=None):
    folder = Path(folder)
    files = files or {
        "index.md": "# Introduction\n\nSee [first steps](./tutorials/first.md#setup) and [the API](api/main).\n",
        "tutorials/first.md": "# First steps\n\n![logo](../imgs/logo.png)\n\n## Setup\n\nBack [home](../index.md).\n",
        "api/main.md": "# Main classes\n",
        "imgs/logo.png": "png",
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "_toctree.yml").write_text(toctree, encoding="utf-8")
    for name, content in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(content, encoding="utf-8")
    return folder


class BuildDocTester(unittest.TestCase):
    def tearDown(self):
        # don't leak a `_config.py` loaded by a test
        with tempfile.TemporaryDirectory() as tmp_dir:
            read_doc_config(tmp_dir)

    def test_re_autodoc(self):
        self.assertEqual(
            _re_autodoc.search("[[autodoc]] transformers.FlaxBertForQuestionAnswering").groups(),
            ("transformers.FlaxBertForQuestionAnswering",),
        )

    def test_re_list_item(self):
        self.assertEqual(_re_list_item.search("   - forward").groups(), ("forward",))

    def test_build_doc_resolves_section_urls(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            docs = write_docs(Path(tmp_dir) / "docs")
            out = Path(tmp_dir) / "out"
            doc_build = build_doc("sample", docs, out, version="v1.0.0")

            self.assertEqual(
                doc_build.toctree.page_map(), {"index": "guide", "tutorials/first": "guide", "api/main": "reference"}
            )
            self.assertEqual(
                sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()),
                ["api/main.mdx", "imgs/logo.png", "index.mdx", "tutorials/first.mdx"],
            )
            index = (out / "index.mdx").read_text(encoding="utf-8")
            self.assertIn("[first steps](/sample/v1.0.0/guide/tutorials/first/#setup)", index)
            self.assertIn("[the API](/sample/v1.0.0/reference/api/main/)", index)
            first = (out / "tutorials" / "first.mdx").read_text(encoding="utf-8")
            self.assertIn("![logo](/sample/v1.0.0/imgs/logo.png)", first)
            self.assertIn("[home](/sample/v1.0.0/guide/)", first)
            # no objects.inv without a Python module
            self.assertFalse((out / "objects.inv").exists())

    def test_build_doc_watch_mode_still_maps_sections(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            docs = write_docs(Path(tmp_dir) / "docs")
            out = Path(tmp_dir) / "out"
            doc_build = build_doc("sample", docs, out, watch_mode=True, files=[docs / "tutorials" / "first.md"])
            self.assertEqual(doc_build.toctree.page_map()["api/main"], "reference")
            self.assertEqual([p.name for p in out.rglob("*.mdx")], ["first.mdx"])
            first = (out / "tutorials" / "first.mdx").read_text(encoding="utf-8")
            self.assertIn("[home](/sample/main/guide/)", first)

    def test_check_toc_integrity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            docs = write_docs(Path(tmp_dir) / "docs")
            out = Path(tmp_dir) / "out"
            build_doc("sample", docs, out, watch_mode=True)
            self.assertEqual(
                check_toc_integrity(docs, out),
                [
                    "index std:doc -1 guide/ Introduction",
                    "tutorials/first std:doc -1 guide/tutorials/first/ First steps",
                    "api/main std:doc -1 reference/api/main/ Main classes",
                ],
            )

            # a page missing from the toctree
            (out / "extra.mdx").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "not present in the table of contents:\n- extra"):
                check_toc_integrity(docs, out)
            (docs / "_config.py").write_text("disable_toc_check = True\n", encoding="utf-8")
            read_doc_config(docs)
            check_toc_integrity(docs, out)

            # a toctree page that does not exist
            (out / "api" / "main.mdx").unlink()
            with self.assertRaisesRegex(RuntimeError, "do not exist:\n- api/main"):
                check_toc_integrity(docs, out)

    def test_build_doc_rejects_old_toctree(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            docs = write_docs(
                Path(tmp_dir), toctree="- title: Get started\n  sections:\n    - local: index\n      title: Home\n"
            )
            with self.assertRaisesRegex(ValueError, "old list format"):
                build_doc("sample", docs, Path(tmp_dir) / "out")

    def test_convert_anchors_mapping_to_sphinx_format(self):
        import doc_builder

        refs = convert_anchors_mapping_to_sphinx_format(
            {
                "doc_builder.build_doc": "reference/api/build/",
                "doc_builder.utils.doc_url": "reference/api/utils/",
                "doc_builder.toctree.TocTree.pages": "reference/api/toctree/#doc_builder.toctree.TocTree.pages",
            },
            doc_builder,
        )
        self.assertEqual(
            refs,
            [
                "doc_builder.build_doc py:function 1 reference/api/build/#$ -",
                "doc_builder.utils.doc_url py:function 1 reference/api/utils/#$ -",
                "doc_builder.toctree.TocTree.pages py:method 1 reference/api/toctree/#doc_builder.toctree.TocTree.pages -",
            ],
        )

    def test_objects_inv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            docs = write_docs(
                Path(tmp_dir) / "docs",
                files={
                    "index.md": "# Introduction\n\nUse [`utils.doc_url`].\n",
                    "tutorials/first.md": "# First steps\n",
                    "api/main.md": "# Main classes\n\n## URLs\n\n[[autodoc]] utils.doc_url\n",
                },
            )
            out = Path(tmp_dir) / "out"
            doc_build = build_doc("doc_builder", docs, out, version="v1.0.0", is_python_module=True)
            self.assertEqual(doc_build.anchors_mapping, {"doc_builder.utils.doc_url": "reference/api/main/"})

            index = (out / "index.mdx").read_text(encoding="utf-8")
            self.assertIn(
                "[utils.doc_url()](/doc_builder/v1.0.0/reference/api/main/#doc_builder.utils.doc_url)", index
            )
            api = (out / "api" / "main.mdx").read_text(encoding="utf-8")
            self.assertIn("## URLs[[doc_builder.utils.doc_url]]", api)
            self.assertIn('<div class="docstring">', api)
            self.assertIn("https://github.com/cerulean-works/doc_builder/blob/main/src/doc_builder/utils.py#L", api)

            data = (out / "objects.inv").read_bytes()
            header, _, compressed = data.partition(b"compressed using zlib.\n")
            self.assertIn(b"# Project: doc_builder\n# Version: v1.0.0\n", header)
            inventory = zlib.decompress(compressed).decode().splitlines()
            self.assertIn("doc_builder.utils.doc_url py:function 1 reference/api/main/#$ -", inventory)
            self.assertIn("index std:doc -1 guide/ Introduction", inventory)
            self.assertTrue(all(".html" not in line for line in inventory))


class AutodocMarkerTester(unittest.TestCase):
    def test_markers_in_code_blocks_are_examples(self):
        content = "\n".join(
            [
                "# Autodoc",
                "",
                "```md",
                "[[autodoc]] Flock",
                "```",
                "",
                "````md",
                "```md",
                "[[autodoc]] Flock",
                "```",
                "[[autodoc]] Flock",
                "````",
                "",
                "~~~",
                "[[autodoc]] Flock",
                "~~~",
            ]
        )
        # no package: any marker outside a code block would raise
        self.assertEqual(resolve_autodoc(content, None), content)

    def test_marker_without_package(self):
        with self.assertRaisesRegex(ValueError, "--not_python_module"):
            resolve_autodoc("# Autodoc\n\n[[autodoc]] Flock\n", None)
