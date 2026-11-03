import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";
import { docsTarget } from "./docs-target.js";

const { project, version } = docsTarget();

export default defineConfig({
	plugins: [sveltekit()],
	define: {
		// Compile-time constants for the (project, version) being built (docs/source/architecture.md, C5).
		__DOCS_PROJECT__: JSON.stringify(project),
		__DOCS_VERSION__: JSON.stringify(version),
		__DOCS_SITE_URL__: JSON.stringify(process.env.DOCS_SITE_URL || "https://docs.cerulean.works"),
	},
	optimizeDeps: {
		// Generated `+page.ts` files import `metadata`, which only exists once mdsvex has run, so
		// Vite's dependency scanner (esbuild, no preprocessing) can't follow them. Merged with
		// SvelteKit's own entries.
		entries: ["!src/routes/**/+page.ts"],
	},
	build: {
		sourcemap: Boolean(process.env.DOCS_SOURCEMAP),
	},
});
