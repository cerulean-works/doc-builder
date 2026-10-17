// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	// Injected at build time via Vite `define` (see vite.config.ts)
	const __DOCS_PROJECT__: string;
	const __DOCS_VERSION__: string;

	namespace App {
		// interface Error {}
		// interface Locals {}
		interface PageData {
			/** Set by every generated `+page.ts` (docs/source/architecture.md, C5). */
			section?: "guide" | "reference";
			title?: string;
			editUrl?: string;
			mdUrl?: string;
			headings?: import("$lib/types").HeadingNode | null;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
