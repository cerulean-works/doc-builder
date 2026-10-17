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
import importlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from doc_builder import build_doc
from doc_builder.mock_imports import mock_deps
from doc_builder.staging import Site, get_docs_path_in_repo, stage_site, write_markdown_exports
from doc_builder.utils import (
    DEFAULT_SITE_URL,
    get_default_branch_name,
    get_project_info,
    locate_kit_folder,
    read_doc_config,
    write_llms_feeds,
)

# The kit (SvelteKit) build currently runs on Vite 7, which requires Node.js >= 20.
MIN_NODE_MAJOR_VERSION = 20

# Build artifacts and dependencies do not need to be staged: `pnpm install` recreates
# node_modules and the build regenerates `.svelte-kit` and `build`.
_KIT_ARTIFACTS = shutil.ignore_patterns("node_modules", ".svelte-kit", "build")

# Only the kit's own files are copied from `src/routes` and `static` (mirrors kit/.gitignore), so pages
# left behind by a local `pnpm run dev:fixture` never leak into a build.
_KIT_OWN_FILES = {
    ("src", "routes"): {"+layout.svelte", "+layout.ts", "+error.svelte"},
    ("static",): {"favicon.png"},
}


def KIT_COPY_IGNORE(directory, names):
    ignored = set(_KIT_ARTIFACTS(directory, names))
    parts = Path(directory).parts
    for suffix, keep in _KIT_OWN_FILES.items():
        if parts[-len(suffix) :] == suffix and parts[-len(suffix) - 1] == "kit":
            ignored.update(name for name in names if name not in keep)
    return ignored


# Project and version names end up in URLs and R2 keys; these match the Worker (worker/src/manifests.ts) and the
# reusable workflows, so anything built here can also be published and served.
_re_project = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_re_version = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


def check_node_and_pnpm():
    """
    Raises if Node.js is missing or older than `MIN_NODE_MAJOR_VERSION`, or if pnpm can't be run.
    """
    try:
        p = subprocess.run(
            [resolve_executable("node"), "-v"],
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        version = p.stdout.strip()
    except Exception as e:
        raise OSError(
            f"This command requires Node.js v{MIN_NODE_MAJOR_VERSION} or newer, but node was not found in your system."
        ) from e

    major = int(version.removeprefix("v").split(".")[0])
    if major < MIN_NODE_MAJOR_VERSION:
        raise OSError(
            f"This command requires Node.js v{MIN_NODE_MAJOR_VERSION} or newer, but the version in your system is "
            f"lower ({version.removeprefix('v')})."
        )
    pnpm_command()


def resolve_executable(executable):
    """
    Resolves `node`/`pnpm` to a full path, which also works on Windows where
    `pnpm` is `pnpm.cmd` (not directly runnable by `subprocess` without a shell).
    """
    resolved = shutil.which(executable)
    if resolved is None:
        raise OSError(f"`{executable}` was not found in your system (PATH).")
    return resolved


def pnpm_command():
    """
    The command that runs pnpm: `pnpm` itself or, when it isn't installed, `corepack pnpm`. Corepack ships with
    Node.js up to v24 and runs the pnpm version pinned in the kit's `package.json`.
    """
    for candidate in (["pnpm"], ["corepack", "pnpm"]):
        if shutil.which(candidate[0]) is not None:
            return [resolve_executable(candidate[0]), *candidate[1:]]
    raise OSError(
        "This command requires pnpm, but neither `pnpm` nor `corepack` was found in your system (PATH). Install it "
        "with `npm install -g pnpm`, or see https://pnpm.io/installation."
    )


def run_pnpm(pnpm_args, cwd, env=None, quiet=True):
    """
    Runs `pnpm <pnpm_args>` in `cwd`. With `quiet=True`, stdout is captured
    (stderr passes through so errors stay visible).
    """
    env = dict(os.environ if env is None else env)
    # Corepack would otherwise ask before downloading the pinned pnpm.
    env.setdefault("COREPACK_ENABLE_DOWNLOAD_PROMPT", "0")
    subprocess.run(
        [*pnpm_command(), *pnpm_args],
        stdout=subprocess.PIPE if quiet else None,
        check=True,
        encoding="utf-8",
        cwd=str(cwd),
        env=env,
    )


def docs_node_env(project, version):
    """
    Environment for the kit build/dev server (contract C5): the SvelteKit base path is `/<DOCS_PROJECT>/<DOCS_VERSION>`.
    """
    env = os.environ.copy()
    env["DOCS_PROJECT"] = project
    env["DOCS_VERSION"] = version
    return env


def require_kit_folder():
    kit_folder = locate_kit_folder()
    if kit_folder is None:
        raise OSError(
            "Building HTML requires the kit subfolder of the doc-builder repo. We couldn't find it with the "
            "doc-builder package installed, so you need to run the command from inside the doc-builder repo."
        )
    return kit_folder


def stage_kit_routes(kit_folder, tmp_dir, mdx_dir, doc_folder, toctree, site):
    """
    Copies the kit (without dependencies/build artifacts) to `<tmp_dir>/kit` and stages the MDX build of `mdx_dir`
    into it (contract C5, see `doc_builder.staging.stage_site`).

    Returns `(kit_dir, markdown_exports)` where `markdown_exports` is a list of `(relative_posix_path, markdown)`
    tuples, relative to the `/<project>/<version>/` base.
    """
    kit_dir = Path(tmp_dir) / "kit"
    shutil.copytree(kit_folder, kit_dir, ignore=KIT_COPY_IGNORE)
    markdown_exports = stage_site(kit_dir, mdx_dir, doc_folder, toctree, site)
    return kit_dir, markdown_exports


def resolve_version(args, default_branch):
    if args.version is not None:
        return args.version
    if args.not_python_module:
        return default_branch
    version = importlib.import_module(args.library_name).__version__
    return default_branch if "dev" in version else f"v{version}"


def check_names(project, version):
    if _re_project.fullmatch(project) is None:
        raise ValueError(f"Invalid project `{project}`: only letters, digits, `_` and `-` are allowed.")
    if _re_version.fullmatch(version) is None or version == "latest":
        raise ValueError(
            f"Invalid version `{version}`: only letters, digits, `.`, `_`, `+` and `-` are allowed, and `latest` is "
            "reserved."
        )


def build_command(args):
    # Mocked heavy dependencies must be set up before the documented library is imported; packages that are actually
    # installed are never mocked.
    if args.mock_deps:
        mock_deps(args.mock_deps.split(","))
    read_doc_config(args.path_to_docs)
    if args.html:
        # Error at the beginning if node is not properly installed or the kit is missing.
        check_node_and_pnpm()
        kit_folder = require_kit_folder()

    project = args.library_name
    default_branch = get_default_branch_name(args.path_to_docs)
    version = resolve_version(args, default_branch)
    check_names(project, version)
    source_ref = args.source_ref or default_branch
    project_info = get_project_info(project, repo=args.repo)

    output_path = Path(args.build_dir) / project / version
    build_kwargs = {
        "version": version,
        "source_ref": source_ref,
        "is_python_module": not args.not_python_module,
        "version_tag_suffix": args.version_tag_suffix,
        "repo": project_info["repo"],
        "emit_warning": args.emit_warning,
    }

    print("Building docs for", project, args.path_to_docs, output_path)
    if not args.html:
        # Only the intermediate MDX build.
        build_doc(project, args.path_to_docs, output_path, clean=args.clean, **build_kwargs)
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        mdx_dir = Path(tmp_dir) / "mdx"
        doc_build = build_doc(project, args.path_to_docs, mdx_dir, **build_kwargs)
        site = Site(
            project=project,
            version=version,
            title=project_info["title"],
            description=project_info["description"],
            repo=project_info["repo"],
            source_ref=source_ref,
            docs_path=get_docs_path_in_repo(args.path_to_docs),
        )
        kit_dir, markdown_exports = stage_kit_routes(
            kit_folder, tmp_dir, mdx_dir, args.path_to_docs, doc_build.toctree, site
        )

        print("Installing node dependencies")
        run_pnpm(["install", "--frozen-lockfile"], cwd=kit_dir)

        print("Building HTML files. This will take a while :-)")
        run_pnpm(["run", "build"], cwd=kit_dir, env=docs_node_env(project, version))

        if output_path.exists():
            shutil.rmtree(output_path)
        shutil.copytree(kit_dir / "build", output_path)

        write_markdown_exports(output_path, markdown_exports)
        write_llms_feeds(
            output_path, markdown_exports, project=project, version=version, site_url=args.site_url, title=site.title
        )
        if (mdx_dir / "objects.inv").is_file():
            shutil.copy(mdx_dir / "objects.inv", output_path / "objects.inv")
        (output_path / "_project.json").write_text(json.dumps(project_info, indent=2) + "\n", encoding="utf-8")


def build_command_parser(subparsers=None):
    if subparsers is not None:
        parser = subparsers.add_parser("build")
    else:
        parser = argparse.ArgumentParser("Doc Builder build command")

    parser.add_argument("library_name", type=str, help="Project name (and the Python package name, if any).")
    parser.add_argument(
        "path_to_docs",
        type=str,
        help="Local path to library documentation. The library should be cloned, and the folder containing the "
        "documentation files should be indicated here.",
    )
    parser.add_argument(
        "--build_dir",
        type=str,
        help="Where the built documentation will be (in `<build_dir>/<project>/<version>/`).",
        default="./build/",
    )
    parser.add_argument(
        "--clean", action="store_true", help="Whether or not to clean the output dir before building MDX files."
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Version of the documentation to generate (`main`, a git tag like `v1.2.0`, or `pr_<N>`). Will default "
        "to the version of the package module (using the default branch name for a version containing dev).",
    )
    parser.add_argument("--html", action="store_true", help="Whether or not to build HTML files instead of MDX files.")
    parser.add_argument(
        "--not_python_module",
        action="store_true",
        help="Whether docs files do NOT have corresponding python module (no autodoc, no `objects.inv`).",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="GitHub repository of the project, as `owner/name`. Overrides `repo` in the docs' `_config.py`; "
        "defaults to `cerulean-works/<project>`.",
    )
    parser.add_argument(
        "--source_ref",
        type=str,
        default=None,
        help="Git sha or ref the source links (autodoc) and edit links point to. Defaults to the default branch.",
    )
    parser.add_argument(
        "--site_url",
        type=str,
        default=DEFAULT_SITE_URL,
        help="Absolute origin of the docs site, used in `llms.txt`.",
    )
    parser.add_argument(
        "--version_tag_suffix",
        type=str,
        default="src/",
        help="Suffix to add after the source ref in the source links. For example, the default `src/` suffix will "
        "result in a base link as `https://github.com/{repo}/blob/{source_ref}/src/`.",
    )
    parser.add_argument(
        "--emit-warning",
        action="store_true",
        help="Emit conversion warnings, such as bare asserts in runnable markdown code blocks.",
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
        parser.set_defaults(func=build_command)
    return parser
