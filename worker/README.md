# cerulean-docs Worker

Serves the static doc-builder sites stored in R2. Routing, the R2 layout and
the manifests are specified in [`docs/source/architecture.md`](../docs/source/architecture.md)
(C1–C3). Two deployments share this code:

| Env          | Worker                  | Bucket                  | Domain                        |
| ------------ | ----------------------- | ----------------------- | ----------------------------- |
| `production` | `cerulean-docs`         | `cerulean-docs`         | `docs.cerulean.works`         |
| `preview`    | `cerulean-docs-preview` | `cerulean-docs-preview` | `docs-preview.cerulean.works` |

```sh
pnpm install
pnpm run typecheck
pnpm test                  # vitest in workerd, in-memory R2 seeded from docs/fixtures/r2-keys.txt
pnpm run deploy:production # wrangler deploy --env production
pnpm run deploy:preview    # wrangler deploy --env preview
```

## Browsing real builds locally

1. Build a version with doc-builder (any project, any docs folder):

   ```sh
   doc-builder build flock ../flock/docs/source --version main --build_dir /tmp/out --html
   ```

2. Seed it into the local R2 state that `wrangler dev` reads
   (`worker/.wrangler/state/v3`). The order matches `publish_docs.yml`:
   assets, HTML, `_project.json` (production only), then the
   `<p>/_versions/<v>` marker. Re-seeding a version removes files that are no
   longer in the build.

   ```sh
   pnpm run seed /tmp/out/flock/main --project flock --version main
   pnpm run seed /tmp/out/flock/v1.0.0 --project flock --version v1.0.0 --commit "$(git -C ../flock rev-parse HEAD)"
   pnpm run seed /tmp/out/flock/pr_12 --project flock --version pr_12 --env preview
   ```

   `<dir>` is the version directory itself (`<build_dir>/<p>/<v>`).
   `--env` defaults to `production`; `--commit` defaults to `local`.

3. Serve it:

   ```sh
   pnpm run dev           # production bindings  -> http://localhost:8787/
   pnpm run dev:preview   # preview bindings     -> http://localhost:8787/ (noindex, robots disallow)
   ```

   Both scripts pass `--var MANIFEST_CACHE_SECONDS:0` so newly seeded versions
   appear without waiting for the 60-second manifest cache. Seeding while
   `wrangler dev` is running is fine.

To start over, delete `worker/.wrangler/state`.
