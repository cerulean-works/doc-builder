import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

import {
	docstringPreprocess,
	mdsvexPreprocess,
	tabsPreprocess,
	hashInCodePreprocess,
} from "./preprocessors/index.js";
import { docsTarget } from "./docs-target.js";

const { project, version } = docsTarget();

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: [
		hashInCodePreprocess,
		docstringPreprocess,
		tabsPreprocess,
		mdsvexPreprocess,
		vitePreprocess({}),
	],

	kit: {
		// Every page is prerendered to `<route>/index.html`; unknown paths get the SPA fallback,
		// which the Worker serves as the version's 404 page (C3).
		adapter: adapter({ fallback: "404.html", strict: true }),

		prerender: {
			// Pages link to `.md` exports and other versions that only exist after Python's
			// post-processing or in R2, so don't follow links; every route is an entry anyway.
			crawl: false,
		},

		paths: {
			// Always `/<project>/<version>`, dev included (C5).
			base: `/${project}/${version}`,
			relative: false,
		},
	},

	onwarn: (warning, handler) => {
		if (
			warning.message.includes("unused export property") ||
			warning.code?.startsWith("a11y") ||
			warning.message.includes("A11y") ||
			// md-generated doc content is full of `<video ... />` style self-closing tags
			warning.code === "element_invalid_self_closing_tag" ||
			// initial-value capture of props is intentional here: doc pages pass static props
			warning.code === "state_referenced_locally"
		) {
			/// Too noisy
			return;
		}
		handler(warning);
	},
};

export default config;
