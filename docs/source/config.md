# _config.py

An optional Python file at the root of the docs folder. doc-builder runs it and reads these variables:

| Variable | Default | Meaning |
|---|---|---|
| `project_title` | the project name | Name shown in the top bar, the browser tab and the projects list. |
| `project_description` | empty | One sentence shown on the docs landing page and in the project switcher. |
| `repo` | `cerulean-works/<project>` | GitHub repository (`owner/name`) for source links and **Edit on GitHub**. The `--repo` flag overrides it. |
| `default_branch_name` | the repo's default branch, else `main` | Branch used for links when no `--source_ref` is given, and as the version name of local builds. |
| `disable_toc_check` | `False` | Allow Markdown files that aren't listed in [`_toctree.yml`](toctree). They are not published. |
| `black_avoid_patterns` | none | Regex patterns that `doc-builder style` should leave alone in code examples. |

Example, the configuration of these docs:

```python
project_title = "doc-builder"
project_description = "Builds and serves the documentation of cerulean-works projects."
repo = "cerulean-works/doc-builder"
```

The title and description come from the build of `main`. Republishing an older tag doesn't bring back an older title.
