# _toctree.yml

`_toctree.yml` sits at the root of the docs folder. It lists every page, which section it belongs to, and the order of the sidebar.

## Format

The file is a mapping with two keys, `guide` and `reference`. Each holds a list of entries:

```yaml
guide:
  - title: Get started
    sections:
      - local: index
        title: Introduction
      - local: quickstart
        title: Quickstart
  - title: Tutorials
    isExpanded: false
    sections:
      - local: tutorials/index
        title: Overview
      - local: tutorials/first-agent
        title: Your first agent
reference:
  - title: API
    sections:
      - local: api/flock
        title: Flock
```

`guide` is required. `reference` may be left out or empty, in which case the site has no Reference tab.

## Entry keys

| Key | Type | Meaning |
|---|---|---|
| `title` | string, required | Text shown in the sidebar. For pages it is also the page's title in the layout. |
| `local` | string | The page's path relative to the docs folder, without extension. An entry with `local` is a page. |
| `sections` | list of entries | Child entries. An entry with `sections` and no `local` is a group heading. |
| `isExpanded` | boolean | Set to `false` to collapse a group in the sidebar until one of its pages is open. |

An entry needs `local`, `sections`, or both. Any other key is an error.

## From file to URL

A page's URL is `/<project>/<version>/<section>/<local>/`. The exception is `index`, which maps to its directory:

| `local` | Section | URL |
|---|---|---|
| `index` | guide | `/flock/main/guide/` |
| `quickstart` | guide | `/flock/main/guide/quickstart/` |
| `tutorials/index` | guide | `/flock/main/guide/tutorials/` |
| `api/flock` | reference | `/flock/main/reference/api/flock/` |

If a section has no `index` page, its root URL (for example `/flock/main/reference/`) redirects to the section's first page.

## Rules

The build stops with a list of every problem it finds when:

- a page file isn't listed, or a listed page doesn't exist. Set `disable_toc_check = True` in [`_config.py`](config) to allow unlisted files; they are then left out of the site.
- a page is listed more than once, including once in each section
- `foo` and `foo/index` are both listed in the same section, since they would share a URL
- `local` has an extension or starts or ends with `/`
- the file still uses the old format: a plain list, or the keys `newlocal`, `local_fw` or `quiz`

## Migrating an old toctree

A toctree from Hugging Face's doc-builder is a plain list. Put its entries under `guide:`, then move the API pages to `reference:`:

```yaml
# before
- title: Get started
  sections:
    - local: index
      title: Introduction
- title: API
  sections:
    - local: main_classes/model
      title: Models

# after
guide:
  - title: Get started
    sections:
      - local: index
        title: Introduction
reference:
  - title: API
    sections:
      - local: main_classes/model
        title: Models
```
