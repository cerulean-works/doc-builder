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
Stand-in for the imaginary `sample` package that `docs/fixtures/source` documents (contract C5 golden test).

The code is a trimmed copy of an early `doc_builder.utils`, so that `get_doc_config` sits on line 106 as in the
original: the fixture's autodoc source link (`src/sample/utils.py#L106`) points there. Keep it on that line when
editing this file.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess

# Unused by the fixture, kept so the file mirrors the original layout.
CACHE_DIR = os.path.expanduser(os.getenv("XDG_CACHE_HOME", "~/.cache"))
SAMPLE_CACHE = os.path.join(CACHE_DIR, "sample")


def get_default_branch_name(repo_folder):
    config = get_doc_config()
    if config is not None and hasattr(config, "default_branch_name"):
        return config.default_branch_name
    try:
        p = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
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


def _parse_version(version):
    """Parses `v1.2.3` into `(1, 2, 3)`."""
    return tuple(int(part) for part in version.lstrip("v").split(".") if part.isdigit())


def update_versions_file(build_path, version, doc_folder):
    """
    Insert new version into _versions.json file of the library
    Assumes that _versions.json exists and has its first entry as main version
    """
    main_branch = get_default_branch_name(doc_folder)
    if version == main_branch:
        return
    with open(os.path.join(build_path, "_versions.json")) as versions_file:
        versions = json.load(versions_file)

        if versions[0]["version"] != main_branch:
            raise ValueError(f"{build_path}/_versions.json does not contain a {main_branch} version")

        main_version, sem_versions = versions[0], versions[1:]
        new_version = {"version": version}
        did_insert = False
        for i, value in enumerate(sem_versions):
            if _parse_version(new_version["version"]) == _parse_version(value["version"]):
                # Nothing to do, the version is here already.
                return
            elif _parse_version(new_version["version"]) > _parse_version(value["version"]):
                sem_versions.insert(i, new_version)
                did_insert = True
                break
        if not did_insert:
            sem_versions.append(new_version)

    with open(os.path.join(build_path, "_versions.json"), "w") as versions_file:
        versions_updated = [main_version] + sem_versions
        json.dump(versions_updated, versions_file)


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


def get_doc_config():
    """
    Returns the `doc_config` if it has been loaded.
    """
    return doc_config
