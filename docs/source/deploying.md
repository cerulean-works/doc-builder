# Deploying doc-builder

This page is for whoever runs `docs.cerulean.works`. It covers the first deployment, how changes to doc-builder reach the live site afterwards, and how to undo a bad change. Projects that only publish their docs need [Publishing a project](publishing) instead.

## What gets deployed

doc-builder has four parts, and only the Worker is deployed in the usual sense:

| Part | Where it runs | How a change reaches production |
|---|---|---|
| **Worker** (`worker/`) | Cloudflare, as two Workers: `cerulean-docs` and `cerulean-docs-preview` | [`deploy_worker.yml`](workflows#deploy-worker) deploys it on every push to `main` that touches `worker/`. |
| **Buckets** | Cloudflare R2: `cerulean-docs` and `cerulean-docs-preview` | Created once, by hand. Projects fill them when they publish. |
| **Python CLI and kit** (`src/`, `kit/`) | Inside each project's docs build, in GitHub Actions | Nothing is released. Each build checks out doc-builder at the ref the project pinned in `uses:`, so a merge to `main` is used by the next build of every project that pins `@main`. |
| **Reusable workflows** (`.github/workflows/`) | Each project's GitHub Actions | Same as the CLI: read at the pinned ref on every run. |

Published docs are never changed by a deployment. Each version keeps the HTML, scripts and styles it was built with until that version is built again (see [How production works](production#how-versions-are-identified)).

## First deployment

Do these steps once, in this order. Run the commands from `worker/` in this repository, after `pnpm install` and `pnpm exec wrangler login`.

### 1. Create the buckets

```bash
pnpm exec wrangler r2 bucket create cerulean-docs
pnpm exec wrangler r2 bucket create cerulean-docs-preview
```

`cerulean-docs` holds production builds and `cerulean-docs-preview` holds PR previews.

### 2. Expire old previews

Previews are deleted when their PR closes. A lifecycle rule also removes anything left behind 30 days after its last upload. Leave the prefix empty so the rule applies to the whole bucket:

```bash
pnpm exec wrangler r2 bucket lifecycle add cerulean-docs-preview expire-previews --expire-days 30
pnpm exec wrangler r2 bucket lifecycle list cerulean-docs-preview
```

Every push to a PR re-uploads all of its files, so an active preview never expires.

### 3. Create the R2 API token

In the dashboard, go to **R2 → Manage API tokens → Create**:
- Give the token **Object Read & Write**, scoped to `cerulean-docs` and `cerulean-docs-preview`.
- Store its access key ID and secret as the organization secrets `DOC_BUILDER_R2_ACCESS_KEY_ID` and `DOC_BUILDER_R2_SECRET_ACCESS_KEY`.
- Store the account ID as the organization secret `CLOUDFLARE_ACCOUNT_ID`.

Make the three secrets available to every repository that publishes docs, including this one.

### 4. Deploy the Worker

```bash
pnpm test
pnpm run deploy:production
pnpm run deploy:preview
```

Until the domains are set up in the next step, the two Workers answer on their `workers.dev` addresses, which wrangler prints after each deploy. Use them to check the deployment:

```bash
curl -s https://cerulean-docs.<your-subdomain>.workers.dev/_projects.json
```

The response is `[]` until a project publishes.

### 5. Point the domains at the Worker

In `worker/wrangler.jsonc`:
1. Uncomment the `routes` entry of each environment: `docs.cerulean.works` for `production` and `docs-preview.cerulean.works` for `preview`. Both use `"custom_domain": true`, and the `cerulean.works` zone must be on the same Cloudflare account.
2. Set `"workers_dev": false`, so the docs are only served on their own domains.

Then deploy both environments again, or merge the change to `main` once step 6 is done.

> [!WARNING]
> Keep previews on their own domain. PR builds run JavaScript from the pull request, and a separate origin is what stops it from reaching anything on the production docs.

### 6. Let CI deploy the Worker

[`deploy_worker.yml`](workflows#deploy-worker) needs two secrets in this repository:
- `CLOUDFLARE_API_TOKEN`: create it from the **Edit Cloudflare Workers** template, and add **Zone → Workers Routes → Edit** for the custom domains.
- `CLOUDFLARE_ACCOUNT_ID`: already available if you added the organization secret in step 3.

From then on, every push to `main` that touches `worker/` runs the Worker's tests and deploys both environments.

### 7. Publish the first docs

This repository publishes its own docs with the same workflows as every project (`.github/workflows/docs.yml`, as project `doc-builder`). Push to `main`, or run the **Docs** workflow from the Actions tab.

### 8. Check it

```bash
curl -sI https://docs.cerulean.works/doc-builder/ | grep -i location
curl -s https://docs.cerulean.works/_projects.json
curl -sI https://docs-preview.cerulean.works/ | grep -i x-robots-tag
```

1. The first command should show a redirect to the default version: `/doc-builder/main/guide/` until doc-builder has a release tag.
2. The second should list `doc-builder`.
3. The third should print `x-robots-tag: noindex`.

Then add the [publishing workflows](publishing) to each project.

## Shipping changes

After the first deployment, changes reach production through `main`:

| You change | What happens after the merge | What to do |
|---|---|---|
| `worker/` | `deploy_worker.yml` tests and deploys both Workers within a few minutes. | Watch the **Deploy Worker** run. Run it by hand from the Actions tab to redeploy without a change. |
| `src/` or `kit/` | The next docs build of each project pinned to `@main` uses the change. | To roll it out now, run each project's **Docs** workflow by hand on `main`. Tags keep their old build unless you also run it on them. |
| `.github/workflows/` | The next run of each project pinned to `@main` uses it. | Check the next build and publish in one project before relying on it. |
| `docs/source/` | `docs.yml` publishes these docs. | Nothing. |

Changes to `src/`, `kit/` and the workflows affect every project at once and can't be tested against them in this repository. Before merging one:
1. Run the full test suite (see [Developing doc-builder](developing)).
2. Build one real project with your branch, for example by pointing its `uses:` at your branch in a PR of that project. Its preview shows the result without touching production.

### Releases

doc-builder isn't published to PyPI. A release is a git tag such as `v1.4.0`:
- Pushing the tag publishes this version of the docs at `/doc-builder/v1.4.0/`.
- Projects that want reproducible builds pin it: `uses: cerulean-works/doc-builder/.github/workflows/build_docs.yml@v1.4.0`. Their builds then only change when they move the pin.

## Undoing a bad change

**The Worker.** Roll back to the previous version without waiting for a fix:

```bash
pnpm exec wrangler deployments list --env production
pnpm exec wrangler rollback --env production
```

`rollback` goes back to the previous version unless you pass a version ID from the list. Repeat with `--env preview`. Revert the change on `main` too, or the next push to `worker/` deploys it again.

**The CLI, the kit or a workflow.** Revert the change on `main`. Then run the **Docs** workflow by hand, on `main` and on any tag, in each project that published a bad build since the change. Projects pinned to a tag or a commit SHA aren't affected.

**A bad build of one version.** Run the **Docs** workflow by hand on that version's branch or tag after the fix, or [remove the version](production#removing-things).

## Watching it

- **Live logs:** `pnpm exec wrangler tail --env production` streams requests and errors as they happen.
- **History:** logs are enabled (`observability` in `wrangler.jsonc`), so recent requests are searchable on each Worker's **Logs** tab in the Cloudflare dashboard.
- **Publishes:** each project's **Docs** run summary links to the version it published.

## Changing names or domains

The bucket names and domains appear in several places. To change one, change all of them in one pull request:

| Name | Where |
|---|---|
| `cerulean-docs`, `cerulean-docs-preview` | `worker/wrangler.jsonc`, `publish_docs.yml`, `delete_pr_docs.yml` |
| `docs.cerulean.works` | `worker/wrangler.jsonc`, the `site_url` defaults of `build_docs.yml` and `publish_docs.yml`, `DEFAULT_SITE_URL` in `src/doc_builder/utils.py` |
| `docs-preview.cerulean.works` | `worker/wrangler.jsonc`, the `preview_site_url` defaults of `build_docs.yml` and `publish_docs.yml` |

Also update these docs and `worker/README.md`. Moving to a new bucket doesn't copy anything: every project then has to publish again.
