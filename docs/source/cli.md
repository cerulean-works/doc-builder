# Command line

Installing doc-builder provides the `doc-builder` command. Every subcommand accepts `--help`.

## build

Builds one version of a project's docs.

```bash
doc-builder build <project> <path_to_docs> [options]
```

`<project>` is the project's name and the first URL segment, made of letters, digits, `_` and `-`. For Python projects it is also the package to import for autodoc.

| Option | Default | Meaning |
|---|---|---|
| `--html` | off | Build the complete site. Without it, only the intermediate MDX files are written. |
| `--build_dir` | `./build/` | The site goes to `<build_dir>/<project>/<version>/`. |
| `--version` | see below | Version name: `main`, a tag such as `v1.2.0`, or `pr_<N>`. Letters, digits, `.`, `_`, `+` and `-`; `latest` is reserved. |
| `--not_python_module` | off | The docs have no Python package: skip autodoc and `objects.inv`. |
| `--repo` | from `_config.py`, else `cerulean-works/<project>` | GitHub repository for source and edit links. |
| `--source_ref` | the default branch | Commit or branch that source and edit links point to. CI passes the commit being built. |
| `--site_url` | `https://docs.cerulean.works` | Absolute origin written into `llms.txt`. |
| `--mock_deps` | none | Comma-separated modules to mock during autodoc, for example `torch,triton`. |
| `--version_tag_suffix` | `src/` | Path inserted after the ref in source links (`…/blob/<ref>/src/…`). |
| `--emit-warning` | off | Report conversion warnings, such as bare `assert`s in runnable code blocks. |
| `--clean` | off | Empty the output folder first (MDX builds only; `--html` always replaces it). |

**Default version:**
- With `--not_python_module`, it is the default branch name.
- Otherwise it comes from the package's `__version__`: `v<version>`, or the default branch name if the version contains `dev`.

**Output** of an `--html` build:

```
build/<project>/<version>/
├── guide/…/index.html, reference/…/index.html   pages
├── guide.md, guide/….md, reference/….md        Markdown export of each page
├── llms.txt, llms-full.txt
├── 404.html
├── _app/                                        scripts and styles
├── pagefind/                                    search index
├── objects.inv                                  Python projects only
└── _project.json
```

## preview

Serves the docs locally and updates them as you edit.

```bash
doc-builder preview <project> <path_to_docs> [--not_python_module] [--mock_deps a,b]
```

Opens on `http://localhost:5173/<project>/main/guide/`. Edited pages are rebuilt one at a time. Changing `_toctree.yml` restages every page. The project and version menus list only the current project and version, because the full lists come from the Worker.

## style

Formats docstrings in Python files and code examples in Markdown files.

```bash
doc-builder style src/flock docs/source --max_len 119
```

| Option | Meaning |
|---|---|
| `--max_len` | Maximum line length. |
| `--check_only` | Report the files that would change, and fail if there are any, without changing them. |
| `--path_to_docs` | Docs folder whose `_config.py` to read (`black_avoid_patterns`). |

It also ships as a [pre-commit](https://pre-commit.com) hook:

```yaml
repos:
  - repo: https://github.com/cerulean-works/doc-builder
    rev: <tag or commit>
    hooks:
      - id: doc-builder-style
        args: [--max_len, "119"]
        files: ^(src|docs/source)/
```

## check-links

Finds internal links that point at pages, anchors or objects that don't exist.

```bash
doc-builder check-links docs/source
```

| Option | Meaning |
|---|---|
| `--package_name` | Import name of the documented package, if it can't be detected. |
| `--format` | `detailed` (default) or `list` (`file:line - url`). |
| `--max_workers` | Parallel workers. |
| `--no-progress` | No progress bar, for CI logs. |

## convert

Converts one file, for example from reStructuredText to MDX.

```bash
doc-builder convert docs/source/old_page.rst
```

| Option | Meaning |
|---|---|
| `--output_file` | Where to write. Defaults to the source file with an `.mdx` suffix. |
| `--package_name` | Package the file belongs to. Defaults to the repository name. |
| `--doc_folder` | The docs folder. Defaults to `docs/source` in the repository. |
