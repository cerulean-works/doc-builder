# Reusable workflows

Projects call these from `cerulean-works/doc-builder/.github/workflows/<file>@<ref>`. [Publishing a project](publishing) shows them wired together.

## build_docs.yml[[build-docs]]

Builds one version with `doc-builder build --html` and uploads the result as the `docs-build` artifact. It holds no secrets, so it is safe to run on pull requests from forks.

| Input | Default | Meaning |
|---|---|---|
| `project` | required | Project name, the first URL segment. |
| `version` | `pr_<N>` on pull requests, the tag on tag pushes, else `main` | Version to build. |
| `source_ref` | triggering commit | Source branch, tag or commit to build. Ignored on pull requests, which always build the PR's head commit. |
| `path_to_docs` | `<repo name>/docs/source` | Docs folder, relative to the workspace. The repository is checked out into a folder named after it. |
| `package_path` | `<repo name>` | What to `pip install`, extras allowed (`flock[docs]`). |
| `python_version` | `3.12` | Python for the build. |
| `not_python_module` | `false` | Skip installing the package and autodoc. |
| `mock_deps` | empty | Modules to mock during autodoc. |
| `version_tag_suffix` | `src/` | Path after the commit in source links (`…/blob/<sha>/src/…`). Set it to `""` when the package sits at the repository root. |
| `pre_command` | empty | Shell command run in the build environment before building. |
| `repo` | the calling repository | `owner/name` to check out and link to. |
| `site_url` | `https://docs.cerulean.works` | Origin for `llms.txt` on non-PR builds. |
| `preview_site_url` | `https://docs-preview.cerulean.works` | Origin for `llms.txt` on PR builds. |

The doc-builder code and UI used for the build are exactly the ones at the ref the caller pinned in `uses:`.

### Rebuild a release with the current theme

Doc-builder's **Docs** workflow accepts a `release_version` when run manually. Select `main` as the workflow branch and enter an existing tag such as `v0.1.0`. It rebuilds that tag's documentation with the builder and theme from `main`, then publishes back to the same versioned URL. Leaving the field empty preserves the usual behavior.

Rebuilding `main` alone does not update released versions. The default docs URL opens the highest stable release, so rebuild that release as well when updating its theme. Running the workflow on the old tag itself uses the old builder too.

## publish_docs.yml[[publish-docs]]

Uploads a `docs-build` artifact to R2.

| Input | Default | Meaning |
|---|---|---|
| `project` | required | Must match the build's `project`. |
| `environment` | required | `production` or `preview`. |
| `version` | the tag on tag pushes, else `main` | Production only. Must match the build if you set it there. |
| `site_url` | `https://docs.cerulean.works` | Used in the run summary. |
| `preview_site_url` | `https://docs-preview.cerulean.works` | Used in the PR comment. |

| Secret | Meaning |
|---|---|
| `r2_access_key_id`, `r2_secret_access_key` | R2 API token with object read and write. Pass the organization secrets `DOC_BUILDER_R2_ACCESS_KEY_ID` and `DOC_BUILDER_R2_SECRET_ACCESS_KEY`. |
| `cloudflare_account_id` | Cloudflare account ID: the organization secret `CLOUDFLARE_ACCOUNT_ID`. |

**Production** runs right after the build in the same workflow. It uploads to `cerulean-docs` in this order:
1. Scripts and other assets.
2. Pages.
3. The project's title and description, from `main` only, or from the first version a project ever publishes.
4. The version marker. This is the moment the version appears in the version list.
5. Files the new build no longer has are deleted. Old script chunks are kept, so readers with a page already open keep working.

**Preview** runs from a `workflow_run` workflow.
- It checks the artifact against the pull request before uploading anything (see [How previews stay safe](publishing#how-previews-stay-safe)).
- It then uploads to `cerulean-docs-preview` and creates or updates a single comment on the PR with the preview link.
- Every file is re-uploaded, so the 30-day expiry restarts on each push.

Both modes run one at a time per project and version.

## delete_pr_docs.yml[[delete-pr-docs]]

Removes a PR's preview: first its version marker, then its files. It also edits the preview comment to say the preview was removed. Call it from `pull_request_target: types: [closed]`. It never checks out code.

| Input | Meaning |
|---|---|
| `project` | Project name. |
| `pr_number` | `${{ github.event.pull_request.number }}` |

It takes the same three secrets as `publish_docs.yml`.
