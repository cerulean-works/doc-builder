# Developing doc-builder

doc-builder has three parts, each with its own tests:

| Directory | What it is | Checks |
|---|---|---|
| `src/doc_builder` | Python CLI: Markdown and docstrings → MDX, staged into the kit | `pytest`, `ruff` |
| `kit` | SvelteKit app: the UI, rendering and search | `svelte-check`, Prettier, ESLint |
| `worker` | Cloudflare Worker: routing, redirects, manifests | Vitest |

They agree on the contracts in [Architecture and contracts](architecture). If you change one side of a contract, update the other side and the fixtures in `docs/fixtures/` in the same change.

## Python

```bash
uv sync --python 3.12 --extra dev
uv run pytest tests/
uv run ruff check src tests && uv run ruff format --check src tests
```

`tests/test_staging.py` is a golden test. It builds `docs/fixtures/source` and compares the output with `docs/fixtures/handoff`, which is exactly what the kit receives.

The end-to-end test builds these docs (`docs/source/`) with `--html` through the real kit. It needs Node and pnpm, and is not part of the default run:

```bash
uv run pytest tests/test_e2e.py -m e2e
```

## Kit

To work on the UI without building a project, run the kit against the handoff fixture:

```bash
cd kit
pnpm install
pnpm run dev:fixture      # http://localhost:5173/sample/v0.1.0/guide/
pnpm run build:fixture    # production build into kit/build
pnpm run check && pnpm run lint && pnpm run eslint
```

The theme comes from the Cerulean design system (`design-system.md` at the repository root). The page chrome lives in `kit/src/lib/chrome/`.

Generated pages may only import a fixed set of components (contract C5). Adding one means changing `src/doc_builder/convert_md_to_mdx.py` and `kit/src/lib` together.

To see these docs with your changes:

```bash
doc-builder preview doc-builder docs/source --not_python_module
```

## Worker

```bash
cd worker
pnpm install
pnpm test
pnpm run seed <build_dir>/<project>/<version> --project <project> --version <version>
pnpm run dev            # http://localhost:8787/
```

`pnpm run seed` uploads a local build into wrangler's local R2 state, in the same order as the publish workflow, so `pnpm run dev` serves it exactly as production would:
- Seed with `--env preview` and run `pnpm run dev:preview` to check preview behavior.
- To start over, delete `worker/.wrangler/state`.

## CI

| Workflow | Runs |
|---|---|
| `test.yml` | Python tests, the end-to-end build of `docs/source/`, Worker tests |
| `quality.yml` | `ruff` |
| `lint-svelte-kit.yml` | kit checks |
| `deploy_worker.yml` | deploys the Worker on pushes to `main` that touch `worker/` |
| `docs.yml`, `docs-pr*.yml` | build and publish these docs, using the same reusable workflows as every other project |
