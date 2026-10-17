# doc-builder

`doc-builder` builds the documentation sites for [cerulean-works](https://github.com/cerulean-works) projects. It turns a project's Markdown pages and Python docstrings into a static site with two sections, **Guide** and **Reference**, for each project and version. The sites are stored in Cloudflare R2 and served by a Cloudflare Worker:

| Deployment | Domain                        | Contents                                                                                       |
| ---------- | ----------------------------- | ---------------------------------------------------------------------------------------------- |
| Production | `docs.cerulean.works`         | `main` and every git tag                                                                       |
| Preview    | `docs-preview.cerulean.works` | one `pr_<N>` build per open pull request, removed when the PR closes and expired after 30 days |

**Documentation: [docs.cerulean.works/doc-builder](https://docs.cerulean.works/doc-builder/).** It is built by doc-builder itself from [`docs/source`](docs/source).

## Quick start

```bash
pip install git+https://github.com/cerulean-works/doc-builder
doc-builder preview <project> docs/source            # live preview at http://localhost:5173/<project>/main/guide/
doc-builder build <project> docs/source --version main --build_dir build --html
```

A docs folder needs a `_toctree.yml` that puts every page in the `guide` or the `reference` section:

```yaml
guide:
  - title: Get started
    sections:
      - local: index
        title: Introduction
reference:
  - title: API
    sections:
      - local: api
        title: Main classes
```

## Repository layout

| Directory                                               | What it is                                                                              |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [`src/doc_builder`](src/doc_builder)                    | Python CLI: converts Markdown and docstrings to MDX and stages them into the kit        |
| [`kit`](kit)                                            | SvelteKit app: renders every page as a full HTML document, with a Pagefind search index |
| [`worker`](worker)                                      | Cloudflare Worker: routing, redirects, version and project manifests, previews          |
| [`.github/workflows`](.github/workflows)                | Reusable build, publish and preview-cleanup workflows for project repos                 |
| [`docs/source`](docs/source)                            | These docs                                                                              |
| [`skills/cerulean-docs`](skills/cerulean-docs/SKILL.md) | Agent skill for writing Cerulean docs; copy it into a repository's `.claude/skills/`    |
| [`docs/fixtures`](docs/fixtures)                        | Golden examples of each handoff, used by the tests of all three parts                   |

## Development

```bash
uv sync --python 3.12 --extra dev
uv run pytest tests/
cd kit && pnpm install && pnpm run dev:fixture
cd worker && pnpm install && pnpm test
```

See [Developing doc-builder](docs/source/developing.md) for the full workflow.

## Acknowledgements

This repo is largely based off of [HuggingFace's doc-builder](https://github.com/huggingface/doc-builder). We thank them for open sourcing their repo!
