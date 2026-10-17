import { getContext, setContext, type Snippet } from "svelte";

/**
 * The layout renders page actions ("Copy page") on the same row as the page's H1. The H1 itself
 * comes from the page content (it is the search result title and an anchor target), so the
 * layout hands the actions to `Heading` through context; `Heading` renders them next to the H1
 * whose anchor matches `local`.
 */
export interface PageTitleContext {
	/** Anchor (`local`) of the page's H1, or null when the content has no H1. */
	readonly local: string | null;
	actions: Snippet;
}

const KEY = Symbol("page-title");

export function setPageTitleContext(context: PageTitleContext) {
	setContext(KEY, context);
}

export function getPageTitleContext(): PageTitleContext | undefined {
	return getContext<PageTitleContext | undefined>(KEY);
}
