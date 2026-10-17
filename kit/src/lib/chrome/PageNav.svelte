<script lang="ts">
	import { page } from "$app/state";
	import { flattenToc, site, withTrailingSlash } from "../site";
	import type { Section } from "../types";

	interface Props {
		section: Section;
	}

	let { section }: Props = $props();

	let pages = $derived(flattenToc(site.toctree[section] ?? []));
	let index = $derived(
		pages.findIndex(
			(entry) => withTrailingSlash(entry.url ?? "") === withTrailingSlash(page.url.pathname)
		)
	);
	let previous = $derived(index > 0 ? pages[index - 1] : undefined);
	let next = $derived(index >= 0 && index < pages.length - 1 ? pages[index + 1] : undefined);
</script>

{#if previous || next}
	<nav class="page-nav" aria-label="Previous and next pages">
		{#if previous}
			<a class="page-nav-link previous" href={previous.url} rel="prev">
				<span class="page-nav-label">Previous</span>
				<span class="page-nav-title">{previous.title}</span>
			</a>
		{/if}
		{#if next}
			<a class="page-nav-link next" href={next.url} rel="next">
				<span class="page-nav-label">Next</span>
				<span class="page-nav-title">{next.title}</span>
			</a>
		{/if}
	</nav>
{/if}
