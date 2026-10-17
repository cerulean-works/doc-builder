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


import argparse
import shutil
import tempfile
import time
from pathlib import Path
from threading import Lock, Thread

from doc_builder import build_doc
from doc_builder.build_doc import CONFIG_FILES, PAGE_SUFFIXES, page_local
from doc_builder.commands.build import (
    check_node_and_pnpm,
    docs_node_env,
    require_kit_folder,
    run_pnpm,
    stage_kit_routes,
)
from doc_builder.mock_imports import mock_deps
from doc_builder.staging import STATIC_DIR, Site, get_docs_path_in_repo, stage_page, stage_site, write_markdown_exports
from doc_builder.utils import (
    find_root_git,
    get_default_branch_name,
    get_project_info,
    is_watchdog_available,
    read_doc_config,
    write_llms_feeds,
)

PREVIEW_VERSION = "main"


class PreviewSite:
    """
    A staged preview: the MDX build in `mdx_dir` and its kit copy in `kit_dir`, kept up to date page by page.
    The Markdown exports and `llms*.txt` are written to the kit's `static/` folder so the dev server serves them.
    """

    def __init__(self, args, tmp_dir, kit_folder):
        self.args = args
        self.doc_folder = Path(args.path_to_docs).absolute()
        self.mdx_dir = Path(tmp_dir) / "mdx"
        self.lock = Lock()

        read_doc_config(self.doc_folder)
        source_ref = get_default_branch_name(self.doc_folder)
        info = get_project_info(args.library_name)
        self.build_kwargs = {
            "version": PREVIEW_VERSION,
            "source_ref": source_ref,
            "is_python_module": not args.not_python_module,
            "repo": info["repo"],
        }
        self.site = Site(
            project=args.library_name,
            version=PREVIEW_VERSION,
            title=info["title"],
            description=info["description"],
            repo=info["repo"],
            source_ref=source_ref,
            docs_path=get_docs_path_in_repo(self.doc_folder),
        )

        print("Initial build docs for", args.library_name, args.path_to_docs)
        self.doc_build = build_doc(args.library_name, self.doc_folder, self.mdx_dir, **self.build_kwargs)
        self.kit_dir, markdown_exports = stage_kit_routes(
            kit_folder, tmp_dir, self.mdx_dir, self.doc_folder, self.doc_build.toctree, self.site
        )
        self.write_exports(markdown_exports)

    def write_exports(self, markdown_exports):
        static_dir = self.kit_dir / STATIC_DIR
        write_markdown_exports(static_dir, markdown_exports)
        write_llms_feeds(
            static_dir, markdown_exports, project=self.site.project, version=self.site.version, title=self.site.title
        )

    def rebuild_all(self):
        """Rebuilds and restages every page, e.g. when `_toctree.yml` changed (pages may move between sections)."""
        self.doc_build = build_doc(
            self.args.library_name, self.doc_folder, self.mdx_dir, watch_mode=True, **self.build_kwargs
        )
        markdown_exports = stage_site(self.kit_dir, self.mdx_dir, self.doc_folder, self.doc_build.toctree, self.site)
        self.write_exports(markdown_exports)

    def rebuild_page(self, src_path):
        """Rebuilds one page and restages its `+page.svelte` and `+page.ts` in its section."""
        local = page_local(src_path, self.doc_folder)
        with tempfile.TemporaryDirectory() as tmp_out:
            build_doc(
                self.args.library_name,
                self.doc_folder,
                tmp_out,
                watch_mode=True,
                files=[src_path],
                anchors_mapping=self.doc_build.anchors_mapping,
                **self.build_kwargs,
            )
            dest = self.mdx_dir / f"{local}.mdx"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(Path(tmp_out) / f"{local}.mdx", dest)

        page = next((page for page in self.doc_build.toctree.pages() if page.local == local), None)
        if page is None:
            print(f"{local} is not in the toctree, it is not staged.")
            return
        markdown_export = stage_page(self.kit_dir, self.mdx_dir, self.doc_folder, self.site, page)
        write_markdown_exports(self.kit_dir / STATIC_DIR, [markdown_export])

    def copy_asset(self, src_path):
        dest = self.kit_dir / STATIC_DIR / src_path.relative_to(self.doc_folder)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src_path, dest)

    def on_change(self, path):
        path = Path(path).absolute()
        if path.suffix == ".py" and str(path) in self.doc_build.source_files_mapping:
            path = Path(self.doc_build.source_files_mapping[str(path)]).absolute()
        if not path.is_file() or not path.is_relative_to(self.doc_folder):
            return
        relative = path.relative_to(self.doc_folder).as_posix()
        if "__" in relative:
            return
        with self.lock:
            try:
                if relative == "_toctree.yml":
                    print("Rebuilding all pages (_toctree.yml changed)")
                    self.rebuild_all()
                elif path.suffix in PAGE_SUFFIXES:
                    print(f"Building: {path}")
                    self.rebuild_page(path)
                elif relative not in CONFIG_FILES:
                    self.copy_asset(path)
            except Exception as e:
                print(f"Error building: {path}\n{e}")


if is_watchdog_available():
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    class WatchEventHandler(FileSystemEventHandler):
        """
        Restages the preview when a doc file (or a Python file documented with autodoc) changes.
        """

        def __init__(self, preview_site):
            super().__init__()
            self.preview_site = preview_site

        def on_created(self, event):
            super().on_created(event)
            if not event.is_directory:
                self.preview_site.on_change(event.src_path)

        def on_modified(self, event):
            super().on_modified(event)
            if not event.is_directory:
                self.preview_site.on_change(event.src_path)


def start_watcher(path, event_handler):
    """
    Starts `pywatchdog.observer` for listening changes in `path`.
    """
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"\nWatching for changes in: {path}\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def start_sveltekit_dev(kit_dir, env):
    """
    Installs sveltekit node dependencies & starts sveltekit in dev mode.
    """
    print("Installing node dependencies")
    run_pnpm(["install", "--frozen-lockfile"], cwd=kit_dir)

    # start sveltekit in dev mode
    run_pnpm(["run", "dev"], cwd=kit_dir, env=env, quiet=False)


def preview_command(args):
    # Mocked heavy dependencies must be set up before the documented library is imported; packages that are actually
    # installed are never mocked.
    if args.mock_deps:
        mock_deps(args.mock_deps.split(","))
    if not is_watchdog_available():
        raise ImportError(
            "Please install `watchdog` to run `doc-builder preview` command.\nYou can do so through pip: `pip install watchdog`"
        )

    # Error at the beginning if node is not properly installed or the kit is missing.
    check_node_and_pnpm()
    kit_folder = require_kit_folder()

    with tempfile.TemporaryDirectory() as tmp_dir:
        preview_site = PreviewSite(args, tmp_dir, kit_folder)

        # Node dev server (daemon: it must not keep the process alive after Ctrl-C)
        env = docs_node_env(args.library_name, PREVIEW_VERSION)
        Thread(target=start_sveltekit_dev, args=(preview_site.kit_dir, env), daemon=True).start()
        print(f"Docs will be served at http://localhost:5173/{args.library_name}/{PREVIEW_VERSION}/guide/")

        watch_folder = find_root_git(args.path_to_docs) or preview_site.doc_folder
        start_watcher(watch_folder, WatchEventHandler(preview_site))


def preview_command_parser(subparsers=None):
    if subparsers is not None:
        parser = subparsers.add_parser("preview")
    else:
        parser = argparse.ArgumentParser("Doc Builder preview command")

    parser.add_argument("library_name", type=str, help="Project name (and the Python package name, if any).")
    parser.add_argument(
        "path_to_docs",
        type=str,
        help="Local path to library documentation. The library should be cloned, and the folder containing the "
        "documentation files should be indicated here.",
    )
    parser.add_argument(
        "--not_python_module",
        action="store_true",
        help="Whether docs files do NOT have corresponding python module (no autodoc).",
    )
    parser.add_argument(
        "--mock_deps",
        type=str,
        default=None,
        help="Comma-separated list of heavy dependencies (e.g. `torch,tensorflow`) to mock instead of importing, so "
        "the documented library can be introspected without installing them. Packages that are actually installed "
        "are never mocked.",
    )

    if subparsers is not None:
        parser.set_defaults(func=preview_command)
    return parser
