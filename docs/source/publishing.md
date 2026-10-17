# Publishing a project

A project publishes its docs by calling doc-builder's reusable GitHub workflows from four small workflow files of its own. This page sets them up for a project called `flock`; replace `flock` with your project's name, which becomes the first segment of every URL.

| When | What runs | Result |
|---|---|---|
| Push to `main` or a tag | build, then publish to production | `docs.cerulean.works/flock/<main or tag>/` |
| A pull request is opened or updated | build only, without secrets | a `docs-build` artifact |
| That PR build succeeds | publish to preview | `docs-preview.cerulean.works/flock/pr_<N>/` and a comment on the PR |
| The PR is closed or merged | delete the preview | preview removed, comment updated |

Previews also expire 30 days after their last push.

> [!NOTE]
> The organization-wide Cloudflare setup (buckets, Worker, domains) is done once for all projects. See [Deploying doc-builder](deploying).

[How production works](production) explains what happens after these workflows run: how the version is named, what lands in R2, and when readers see it.

## Before you start

1. The docs folder is in place and builds locally. See the [Quickstart](quickstart).
2. These secrets are available to the repository, ideally as organization secrets:

   | Secret | Value |
   |---|---|
   | `DOC_BUILDER_R2_ACCESS_KEY_ID` | access key of an R2 API token with object read and write on both buckets |
   | `DOC_BUILDER_R2_SECRET_ACCESS_KEY` | its secret |
   | `CLOUDFLARE_ACCOUNT_ID` | the Cloudflare account ID |

   The build workflow never sees them, only the publish and delete workflows do.

## Releases and `main`

`.github/workflows/docs.yml`:

```yaml
name: Docs

on:
  push:
    branches: [main]
    tags: ["v*"]
  # Run by hand on main, or on a tag to rebuild that version.
  workflow_dispatch:

permissions: {}

# One run per ref at a time, in push order, so an older build never publishes over a newer one.
concurrency:
  group: docs-${{ github.ref }}
  cancel-in-progress: false

jobs:
  build:
    uses: cerulean-works/doc-builder/.github/workflows/build_docs.yml@main
    permissions:
      contents: read
    with:
      project: flock
      # package_path: "flock[docs]"   # what to pip install (default: the repo root)
      # not_python_module: true       # docs without autodoc
      # mock_deps: torch,triton       # heavy imports to mock during autodoc

  publish:
    needs: build
    uses: cerulean-works/doc-builder/.github/workflows/publish_docs.yml@main
    permissions: {}
    with:
      project: flock
      environment: production
    secrets:
      r2_access_key_id: ${{ secrets.DOC_BUILDER_R2_ACCESS_KEY_ID }}
      r2_secret_access_key: ${{ secrets.DOC_BUILDER_R2_SECRET_ACCESS_KEY }}
      cloudflare_account_id: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

To rebuild a version without pushing, for example to pick up a doc-builder fix, run the **Docs** workflow from the Actions tab: on `main`, or on a tag to rebuild that tag.

Tags become versions as they are named (`v1.2.0` → `/flock/v1.2.0/`). Once a project has a stable tag, the highest one becomes the default version that `/flock` opens. Prereleases such as `v2.0.0rc1` are listed but never become the default.

> [!TIP]
> Pin `@main`, or a commit SHA for reproducible builds. The ref you pin also selects the doc-builder code and UI that build your docs.

## Pull request previews

Previews use three workflows. Building the PR's code and publishing it happen in separate workflows, so code from a fork never runs where the secrets are.

`.github/workflows/docs-pr.yml` builds the PR, without secrets:

```yaml
name: Docs PR build

on:
  pull_request:

permissions: {}

concurrency:
  group: docs-pr-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  build:
    uses: cerulean-works/doc-builder/.github/workflows/build_docs.yml@main
    permissions:
      contents: read
    with:
      project: flock
```

`.github/workflows/docs-pr-publish.yml` publishes the preview once that build succeeds. The name under `workflows:` must match the build workflow's `name:`.

```yaml
name: Docs PR publish

on:
  workflow_run:
    workflows: ["Docs PR build"]
    types: [completed]

permissions: {}

jobs:
  publish:
    uses: cerulean-works/doc-builder/.github/workflows/publish_docs.yml@main
    permissions:
      actions: read          # download the PR build's artifact
      pull-requests: write   # verify the PR and post the preview comment
    with:
      project: flock
      environment: preview
    secrets:
      r2_access_key_id: ${{ secrets.DOC_BUILDER_R2_ACCESS_KEY_ID }}
      r2_secret_access_key: ${{ secrets.DOC_BUILDER_R2_SECRET_ACCESS_KEY }}
      cloudflare_account_id: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

`.github/workflows/docs-pr-delete.yml` removes the preview when the PR closes. It never checks out code:

```yaml
name: Docs PR cleanup

on:
  pull_request_target:
    types: [closed]

permissions: {}

jobs:
  delete:
    uses: cerulean-works/doc-builder/.github/workflows/delete_pr_docs.yml@main
    permissions:
      pull-requests: write
    with:
      project: flock
      pr_number: ${{ github.event.pull_request.number }}
    secrets:
      r2_access_key_id: ${{ secrets.DOC_BUILDER_R2_ACCESS_KEY_ID }}
      r2_secret_access_key: ${{ secrets.DOC_BUILDER_R2_SECRET_ACCESS_KEY }}
      cloudflare_account_id: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

## How previews stay safe

The PR build runs code from the PR, which may come from a fork, so publishing treats its output as untrusted:

- The PR number and commit stored in the artifact must be well-formed. They must also match an **open** PR whose head is exactly the commit that was built.
- The project name always comes from your workflow file, never from the artifact.
- Previews are served from a separate domain, so a PR's JavaScript can never run on the production docs.
- Search engines are told not to index previews.

## Customizing the build

[`build_docs.yml`](workflows#build-docs) also accepts:
- `path_to_docs`, if your docs aren't in `docs/source`
- `python_version`
- `pre_command`, a shell command run before the build, for example to generate files
- `version`, to override the version name

If you pass `version` on push, pass the same value to `publish_docs.yml`. All inputs are listed in [Reusable workflows](workflows).
