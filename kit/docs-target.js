import { readFileSync } from "node:fs";

/**
 * The (project, version) being built. doc-builder sets DOCS_PROJECT / DOCS_VERSION
 * (docs/source/architecture.md, C5); without them (`pnpm run check`, a bare `pnpm run dev`) this falls
 * back to the staged site metadata so the base path keeps its production shape.
 * @returns {{ project: string, version: string }}
 */
export function docsTarget() {
	/** @type {{ project?: string, version?: string }} */
	let site = {};
	try {
		const url = new URL("./src/lib/generated/site.json", import.meta.url);
		site = JSON.parse(readFileSync(url, "utf8"));
	} catch {
		// no staged site metadata
	}
	return {
		project: process.env.DOCS_PROJECT || site.project || "docs",
		version: process.env.DOCS_VERSION || site.version || "main",
	};
}
