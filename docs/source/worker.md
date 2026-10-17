# Worker

The Cloudflare Worker in `worker/` serves every published build from R2. [How production works](production) explains how it fits with the build and publish steps. The same code runs twice:

| Environment | Domain | Bucket | Differences |
|---|---|---|---|
| `production` | `docs.cerulean.works` | `cerulean-docs` | none |
| `preview` | `docs-preview.cerulean.works` | `cerulean-docs-preview` | `X-Robots-Tag: noindex` on every response, and a `robots.txt` that disallows everything |

## Routes

| Request | Response |
|---|---|
| `/` | Landing page listing every project. |
| `/_projects.json` | Project list (see [Manifests](#manifests)). |
| `/<p>`, `/<p>/` | 302 to `/<p>/<default>/guide/` |
| `/<p>/_versions.json` | Version list for one project. |
| `/<p>/latest/<rest>` | 302 to `/<p>/<default>/<rest>` |
| `/<p>/guide/<rest>`, `/<p>/reference/<rest>` | 302 to the same path under the default version |
| `/<p>/<v>`, `/<p>/<v>/` | 302 to `/<p>/<v>/guide/` |
| `/<p>/<v>/<path>/` | The page at `<p>/<v>/<path>/index.html` |
| `/<p>/<v>/<path>.<ext>` | The file itself |
| `/<p>/<v>/<path>` | 308 to `/<p>/<v>/<path>/` |

Two kinds of missing page are handled differently:
- A missing page inside an existing version gets that version's own `404.html`, styled like the docs, with status 404.
- Anything else gets the Worker's built-in 404 page.

## Default version

`/<p>` and `latest` resolve to the highest stable tag, compared as version numbers (`v1.10.0` > `v1.9.2`):
- Tags with a prerelease suffix (`-rc.1`, `rc1`, `a1`, `b2`, `.dev0`) are listed but never chosen.
- Without a stable tag, the default is `main`.
- On the preview domain, which has no `main`, it is the newest PR.

## Manifests

`/<p>/_versions.json`:

```json
{
  "default": "v1.2.0",
  "versions": [
    { "version": "main", "commit": "3f2a…", "built_at": "2026-10-17T08:23:15Z" },
    { "version": "v1.2.0", "commit": "9c1d…", "built_at": "2026-10-02T11:04:51Z" }
  ]
}
```

`/_projects.json`:

```json
[{ "name": "flock", "title": "Flock", "description": "…", "repo": "cerulean-works/flock", "default": "v1.2.0" }]
```

Nothing stores these lists. The Worker builds them from R2:
- **Versions:** each published version has a marker object at `<p>/_versions/<v>`, written last by the publish workflow. Versions that are still uploading stay hidden.
- **Projects:** the top-level folders, plus each project's `_project.json`.

The lists are cached for up to 60 seconds, so a newly published version can take a minute to appear in the switcher.

## Caching and headers

| Files | `Cache-Control` |
|---|---|
| `_app/immutable/**` (content-hashed) | `public, max-age=31536000, immutable` |
| Pages, `.md` exports, `llms*.txt`, `_app/version.json` | `public, max-age=60` |
| Other files (images, search index, …) | `public, max-age=300` |

Every file response carries an `ETag` and `Last-Modified`, and conditional requests get `304 Not Modified`.

A page requested with `Accept: text/markdown` (and not `text/html`) returns its Markdown export, which is handy for tools and AI agents:

```bash
curl -H "Accept: text/markdown" https://docs.cerulean.works/doc-builder/main/guide/quickstart/
```

## Running it locally

```bash
cd worker
pnpm install
pnpm run seed ../build/doc-builder/main --project doc-builder --version main
pnpm run dev    # http://localhost:8787/
```

`seed` writes a build into wrangler's local R2 state, in the same order as the publish workflow. Use `--env preview` with `pnpm run dev:preview` to try the preview environment.
