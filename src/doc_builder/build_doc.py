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


import importlib
import os
import posixpath
import re
import shutil
import zlib
from pathlib import Path
from typing import NamedTuple

from tqdm import tqdm

from .autodoc import autodoc_svelte, find_object_in_package, get_source_path, resolve_links_in_text
from .convert_md_to_mdx import convert_md_to_mdx
from .convert_rst_to_mdx import convert_rst_to_mdx, find_indent, is_empty_line
from .toctree import TocTree, load_toctree
from .utils import DEFAULT_REPO_OWNER, doc_url, get_doc_config, page_route, read_doc_config, update_fence

_re_autodoc = re.compile(r"^\s*\[\[autodoc\]\]\s+(\S+)\s*$")
_re_list_item = re.compile(r"^\s*-\s+(\S+)\s*$")

PAGE_SUFFIXES = (".md", ".mdx", ".rst")
# Files of the docs folder that configure the build: they are neither pages nor assets.
CONFIG_FILES = ("_toctree.yml", "_config.py")


class DocBuild(NamedTuple):
    toctree: TocTree
    # anchor of a documented object -> page URL relative to the `/<project>/<version>/` base (with `#anchor` when
    # it differs from the object's own anchor)
    anchors_mapping: dict
    # source file of a documented object -> doc page that documents it
    source_files_mapping: dict


def page_local(file, doc_folder):
    """The toctree `local` of a page source file."""
    return Path(file).with_suffix("").relative_to(doc_folder).as_posix()


def resolve_autodoc(content, package, return_anchors=False, page_info=None, version_tag_suffix="src/"):
    """
    Replaces [[autodoc]] special syntax by the corresponding generated documentation in some content.

    Args:
        content (`str`): The documentation to treat.
        package (`types.ModuleType`): The package where to look for objects to document.
        return_anchors (`bool`, *optional*, defaults to `False`):
            Whether or not to return the list of anchors generated.
        page_info (`Dict[str, str]`, *optional*): Some information about the page.
        version_tag_suffix (`str`, *optional*, defaults to `"src/"`):
            Suffix to add after the source ref (e.g. a commit sha or main) in the source links.
            For example, the default `"src/"` suffix will result in a base link as `https://github.com/{repo}/blob/{source_ref}/src/`.
            For example, `version_tag_suffix=""` will result in a base link as `https://github.com/{repo}/blob/{source_ref}/`.
    """
    idx_last_heading = None
    fence = None
    lines = content.split("\n")
    new_lines = []
    source_files = None
    if return_anchors:
        anchors = []
        errors = []
    idx = 0
    while idx < len(lines):
        # `[[autodoc]]` inside a code block is an example of the syntax, not a marker
        if fence is None and _re_autodoc.search(lines[idx]) is not None:
            object_name = _re_autodoc.search(lines[idx]).groups()[0]
            if package is None:
                raise ValueError(
                    f"`[[autodoc]] {object_name}` needs a Python package to document, but the docs are built with "
                    "`--not_python_module`."
                )
            autodoc_indent = find_indent(lines[idx])
            idx += 1
            while idx < len(lines) and is_empty_line(lines[idx]):
                idx += 1
            if (
                idx < len(lines)
                and find_indent(lines[idx]) > autodoc_indent
                and _re_list_item.search(lines[idx]) is not None
            ):
                methods = []
                methods_indent = find_indent(lines[idx])
                while is_empty_line(lines[idx]) or (
                    find_indent(lines[idx]) == methods_indent and _re_list_item.search(lines[idx]) is not None
                ):
                    if not is_empty_line(lines[idx]):
                        methods.append(_re_list_item.search(lines[idx]).groups()[0])
                    idx += 1
                    if idx >= len(lines):
                        break
            else:
                methods = None
            doc = autodoc_svelte(
                object_name,
                package,
                methods=methods,
                return_anchors=return_anchors,
                page_info=page_info,
                version_tag_suffix=version_tag_suffix,
            )
            if return_anchors:
                if len(doc[1]) and idx_last_heading is not None:
                    object_anchor = doc[1][0]
                    new_lines[idx_last_heading] += f"[[{object_anchor}]]"
                    idx_last_heading = None
                anchors.extend(doc[1])
                errors.extend(doc[2])
                doc = doc[0]
            new_lines.append(doc)

            try:
                source_files = source_files = get_source_path(object_name, package)
            except (AttributeError, OSError, TypeError):
                # tokenizers obj do NOT have `__module__` attribute & can NOT be used with inspect.getfile
                source_files = None
        else:
            new_lines.append(lines[idx])
            fence = update_fence(lines[idx], fence)
            if lines[idx].startswith("#") and fence is None:
                idx_last_heading = len(new_lines) - 1
            idx += 1

    new_content = "\n".join(new_lines)

    return (new_content, anchors, source_files, errors) if return_anchors else new_content


def build_mdx_files(package, doc_folder, output_dir, page_info, version_tag_suffix, files=None):
    """
    Build the MDX files for a given package.

    Args:
        package (`types.ModuleType`): The package where to look for objects to document.
        doc_folder (`str` or `os.PathLike`): The folder where the doc source files are.
        output_dir (`str` or `os.PathLike`): The folder where to put the files built.
        page_info (`Dict[str, str]`): Some information about the page.
        version_tag_suffix (`str`, *optional*, defaults to `"src/"`):
            Suffix to add after the source ref (e.g. a commit sha or main) in the source links.
            For example, the default `"src/"` suffix will result in a base link as `https://github.com/{repo}/blob/{source_ref}/src/`.
            For example, `version_tag_suffix=""` will result in a base link as `https://github.com/{repo}/blob/{source_ref}/`.
        files (`List[os.PathLike]`, *optional*): Only build those files of `doc_folder` (defaults to all of them).
    """
    doc_folder = Path(doc_folder)
    output_dir = Path(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    anchor_mapping = {}
    source_files_mapping = {}

    if "package_name" not in page_info:
        page_info["package_name"] = package.__name__
    page_map = page_info.get("page_map", {})

    all_files = list(doc_folder.glob("**/*")) if files is None else [Path(f) for f in files]
    all_errors = []
    for file in tqdm(all_files, desc="Building the MDX files"):
        new_anchors = None
        errors = None
        section = None
        relative_path = file.relative_to(doc_folder)
        page_info["path"] = file
        try:
            if file.suffix in PAGE_SUFFIXES:
                local = page_local(file, doc_folder)
                section = page_map.get(local)
                dest_file = output_dir / f"{local}.mdx"
                page_info["page_dir"] = posixpath.dirname(local)
                if section is not None:
                    page_info["page_url"] = doc_url(
                        page_info["package_name"], page_info.get("version", "main"), section, local
                    )
                os.makedirs(dest_file.parent, exist_ok=True)
                if file.suffix == ".rst":
                    with open(file, encoding="utf-8") as reader:
                        content = convert_rst_to_mdx(reader.read(), page_info)
                else:
                    with open(file, encoding="utf-8-sig") as reader:
                        content = convert_md_to_mdx(reader.read(), page_info)
                content, new_anchors, source_files, errors = resolve_autodoc(
                    content, package, return_anchors=True, page_info=page_info, version_tag_suffix=version_tag_suffix
                )
                if source_files is not None:
                    source_files_mapping[source_files] = str(file)
                with open(dest_file, "w", encoding="utf-8") as writer:
                    writer.write(content)
                # Make sure we clean up for next page.
                del page_info["page_dir"]
                page_info.pop("page_url", None)
            elif (
                file.is_file()
                and "__" not in relative_path.as_posix()
                and relative_path.as_posix() not in CONFIG_FILES
            ):
                # __ is a reserved svelte file/folder prefix
                dest_file = output_dir / relative_path
                os.makedirs(dest_file.parent, exist_ok=True)
                shutil.copy(file, dest_file)

        except Exception as e:
            message = f"There was an error when converting {file} to the MDX format.\n{e}"
            try:
                error = type(e)(message)
            except Exception:
                # exception types whose constructor takes other arguments (e.g. UnicodeDecodeError)
                error = RuntimeError(message)
            raise error from e

        if new_anchors is not None and section is not None:
            page = f"{page_route(section, local)}/"
            for anchor in new_anchors:
                if isinstance(anchor, tuple):
                    anchor_mapping.update({a: f"{page}#{anchor[0]}" for a in anchor[1:] if a not in anchor_mapping})
                    anchor = anchor[0]
                anchor_mapping[anchor] = page

        if errors is not None:
            all_errors.extend(errors)

    if len(all_errors) > 0:
        raise ValueError(
            "The deployment of the documentation will fail because of the following errors:\n" + "\n".join(all_errors)
        )

    return anchor_mapping, source_files_mapping


def resolve_links(doc_folder, package, mapping, page_info):
    """
    Resolve links of the form [`SomeClass`] to the link in the documentation to `SomeClass` for all files in a
    folder.

    Args:
        doc_folder (`str` or `os.PathLike`): The folder in which to look for files.
        package (`types.ModuleType`): The package in which to search objects for.
        mapping (`Dict[str, str]`): The map from anchor names of objects to their page in the documentation.
        page_info (`Dict[str, str]`): Some information about the page.
    """
    doc_folder = Path(doc_folder)
    all_files = list(doc_folder.glob("**/*.mdx"))
    for file in tqdm(all_files, desc="Resolving internal links"):
        with open(file, encoding="utf-8") as reader:
            content = reader.read()
        content = resolve_links_in_text(content, package, mapping, page_info)
        with open(file, "w", encoding="utf-8") as writer:
            writer.write(content)


def build_doc(
    package_name,
    doc_folder,
    output_dir,
    clean=True,
    version="main",
    source_ref="main",
    is_python_module=False,
    watch_mode=False,
    version_tag_suffix="src/",
    repo=None,
    emit_warning=False,
    files=None,
    anchors_mapping=None,
):
    """
    Build the documentation of a package into MDX files (one per page, at `<output_dir>/<local>.mdx`), copy the other
    files of the docs folder, and write `objects.inv` for Python modules.

    Args:
        package_name (`str`): The name of the package (also the project name in URLs).
        doc_folder (`str` or `os.PathLike`): The folder in which the source documentation of the package is.
        output_dir (`str` or `os.PathLike`):
            The folder in which to put the built documentation. Will be created if it does not exist.
        clean (`bool`, *optional*, defaults to `True`):
            Whether or not to delete the content of the `output_dir` if that directory exists.
        version (`str`, *optional*, defaults to `"main"`): The name of the version of the doc.
        source_ref (`str`, *optional*, defaults to `"main"`):
            The git ref (sha, tag or branch) the source links of the autodoc point to.
        is_python_module (`bool`, *optional*, defaults to `False`):
            Whether the docs being built are for python module.
        watch_mode (`bool`, *optional*, default to `False`):
            If `True`, disables the toc tree check and sphinx objects.inv builds since they are not needed
            when this mode is active.
        version_tag_suffix (`str`, *optional*, defaults to `"src/"`):
            Suffix to add after the source ref in the source links. For example, the default `"src/"` suffix will
            result in a base link as `https://github.com/{repo}/blob/{source_ref}/src/`.
        repo (`str`, *optional*, defaults to `"cerulean-works/{package_name}"`): The GitHub repository (`owner/name`).
        emit_warning (`bool`, *optional*, defaults to `False`):
            Whether to emit documentation conversion warnings such as bare
            ``assert`` in runnable code blocks.
        files (`List[os.PathLike]`, *optional*): Only build those files of `doc_folder` (used by the preview watcher).
        anchors_mapping (`Dict[str, str]`, *optional*):
            Anchors of a previous build, used to resolve links to objects documented on pages not built now.

    Returns:
        `DocBuild`: the toctree, the anchors mapping and the source files mapping.
    """
    read_doc_config(doc_folder)
    toctree = load_toctree(doc_folder)
    page_info = {
        "version": version,
        "source_ref": source_ref,
        "package_name": package_name,
        "repo": repo or f"{DEFAULT_REPO_OWNER}/{package_name}",
        "emit_warning": emit_warning,
        "page_map": toctree.page_map(),
    }
    if clean and Path(output_dir).exists():
        shutil.rmtree(output_dir)

    package = importlib.import_module(package_name) if is_python_module else None
    new_anchors, source_files_mapping = build_mdx_files(
        package, doc_folder, output_dir, page_info, version_tag_suffix=version_tag_suffix, files=files
    )
    anchors_mapping = {**(anchors_mapping or {}), **new_anchors}
    if not watch_mode:
        sphinx_refs = check_toc_integrity(doc_folder, output_dir, toctree)

    if is_python_module:
        if not watch_mode:
            sphinx_refs.extend(convert_anchors_mapping_to_sphinx_format(anchors_mapping, package))
            build_sphinx_objects_ref(sphinx_refs, output_dir, page_info)
        resolve_links(output_dir, package, anchors_mapping, page_info)

    return DocBuild(toctree, anchors_mapping, source_files_mapping)


def check_toc_integrity(doc_folder, output_dir, toctree=None):
    """
    Checks all the MDX files obtained after building the documentation are present in the table of contents, that
    all pages of the table of contents exist, and that no `foo` page coexists with a `foo/index` page.

    Args:
        doc_folder (`str` or `os.PathLike`): The folder where the source files of the documentation lie.
        output_dir (`str` or `os.PathLike`): The folder where the doc is built.
        toctree (`TocTree`, *optional*): The parsed toctree (loaded from `doc_folder` if not provided).

    Returns:
        `List[str]`: the sphinx `std:doc` references, one per page.
    """
    output_dir = Path(output_dir)
    doc_files = [f.relative_to(output_dir).with_suffix("").as_posix() for f in output_dir.glob("**/*.mdx")]
    toc_file = Path(doc_folder) / "_toctree.yml"
    if toctree is None:
        toctree = load_toctree(doc_folder)
    pages = toctree.pages()

    toc_locals = {page.local for page in pages}
    files_not_in_toc = [f for f in doc_files if f not in toc_locals and not f.endswith("README")]
    doc_config = get_doc_config()
    disable_toc_check = getattr(doc_config, "disable_toc_check", False)
    if len(files_not_in_toc) > 0 and not disable_toc_check:
        message = "\n".join([f"- {f}" for f in files_not_in_toc])
        raise RuntimeError(
            "The following files are not present in the table of contents:\n" + message + f"\nAdd them to {toc_file}."
        )

    files_not_exist = [page.local for page in pages if page.local not in doc_files]
    if len(files_not_exist) > 0:
        message = "\n".join([f"- {f}" for f in files_not_exist])
        raise RuntimeError(
            "The following files are present in the table of contents but do not exist:\n"
            + message
            + f"\nRemove them from {toc_file}."
        )

    # One sphinx ref per page, with its URL relative to the `/<project>/<version>/` base.
    return [f"{page.local} std:doc -1 {page_route(page.section, page.local)}/ {page.title}" for page in pages]


def convert_anchors_mapping_to_sphinx_format(anchors_mapping, package):
    """
    Convert the anchor mapping to the format expected by sphinx for the `objects.inv` file.

    Args:
        anchors_mapping (Dict[`str`, `str`]):
            The mapping between anchors for objects in the doc and their location in the doc.
        package (`types.ModuleType`):
            The package in which to search objects for.
    """
    sphinx_refs = []
    for anchor, url in anchors_mapping.items():
        obj = find_object_in_package(anchor, package)
        if isinstance(obj, property):
            obj = obj.fget

        # Object type
        if isinstance(obj, type):
            obj_type = "py:class"
        elif hasattr(obj, "__name__") and hasattr(obj, "__qualname__"):
            obj_type = "py:method" if obj.__name__ != obj.__qualname__ else "py:function"
        else:
            # Default to function (this part is never hit when building the docs for Transformers and Datasets)
            # so it's just to be extra defensive
            obj_type = "py:function"

        if "#" in url:
            sphinx_refs.append(f"{anchor} {obj_type} 1 {url} -")
        else:
            sphinx_refs.append(f"{anchor} {obj_type} 1 {url}#$ -")

    return sphinx_refs


def build_sphinx_objects_ref(sphinx_refs, output_dir, page_info):
    """
    Saves the sphinx references in an `objects.inv` file that can then be used by other documentations powered by
    sphinx to link to objects in the generated doc.

    Args:
        sphinx_refs (`List[str]`): The list of all references, in the format expected by sphinx.
        output_dir (`str` or `os.PathLike`): The folder where the doc is built.
        page_info (`Dict[str, str]`): Some information about the doc.
    """
    intro = [
        "# Sphinx inventory version 2\n",
        f"# Project: {page_info['package_name']}\n",
        f"# Version: {page_info['version']}\n",
        "# The remainder of this file is compressed using zlib.\n",
    ]
    lines = [str.encode(line) for line in intro]

    data = "\n".join(sorted(sphinx_refs)) + "\n"
    data = zlib.compress(str.encode(data))

    with open(Path(output_dir) / "objects.inv", "wb") as f:
        f.writelines(lines)
        f.write(data)
