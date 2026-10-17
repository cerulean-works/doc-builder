# Quickstart

This page walks through adding docs to a project and previewing them on your machine. It takes about five minutes. Publishing them is covered in [Publishing a project](publishing).

## Install

You need Python 3.10 or newer, Node.js 20 or newer and [pnpm](https://pnpm.io/installation). Node and pnpm are needed for previews and HTML builds. Without pnpm installed, doc-builder runs it through Node's built-in `corepack`, which is included up to Node.js 24.

```bash
pip install git+https://github.com/cerulean-works/doc-builder
```

## Create the docs folder

By convention docs live in `docs/source/`. Create three files there.

`docs/source/_toctree.yml` lists every page, under either `guide` or `reference`:

```yaml
guide:
  - title: Get started
    sections:
      - local: index
        title: Introduction
      - local: install
        title: Installation
reference:
  - title: API
    sections:
      - local: api
        title: Main classes
```

`docs/source/index.md` is the first page of the Guide:

```md
# Introduction

Flock runs many small agents together. Start with the [installation](install) guide.
```

`docs/source/install.md` and `docs/source/api.md` are ordinary Markdown pages. Each page starts with a single `#` title.

Optionally, `docs/source/_config.py` names the project and its repository:

```python
project_title = "Flock"
project_description = "Run many small agents together."
repo = "cerulean-works/flock"
```

## Preview

```bash
doc-builder preview flock docs/source
```

Open `http://localhost:5173/flock/main/guide/`.

- Edited pages update as you save.
- When you change `_toctree.yml`, the whole site is restaged.
- If the project isn't a Python package, or you don't want autodoc yet, add `--not_python_module`.

> [!TIP]
> Every page must appear in `_toctree.yml` exactly once. If it doesn't, the build stops and lists the page that is missing or extra.

## Build

```bash
doc-builder build flock docs/source --version main --build_dir build --html
```

The complete site is written to `build/flock/main/`. You normally let CI run this; see [Publishing a project](publishing).

## Next steps

- Write pages with callouts, tabs, diagrams and more: [Writing pages](writing).
- Generate reference pages from your docstrings: [Documenting a Python API](api-docs).
- Set up the GitHub workflows: [Publishing a project](publishing).
