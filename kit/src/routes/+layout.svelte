<script lang="ts">
	// Self-hosted type: Newsreader (editorial) and DM Sans (utility); KaTeX for math.
	import "@fontsource/newsreader/400.css";
	import "@fontsource/newsreader/400-italic.css";
	import "@fontsource/newsreader/500.css";
	import "@fontsource/newsreader/600.css";
	import "@fontsource/dm-sans/400.css";
	import "@fontsource/dm-sans/500.css";
	import "@fontsource/dm-sans/600.css";
	import "katex/dist/katex.min.css";
	import "../app.css";
	import { base } from "$app/paths";
	import { afterNavigate } from "$app/navigation";
	import { page } from "$app/state";
	import CopyLLMTxtMenu from "$lib/CopyLLMTxtMenu.svelte";
	import EditOnGithub from "$lib/EditOnGithub.svelte";
	import OnThisPage from "$lib/chrome/OnThisPage.svelte";
	import PageNav from "$lib/chrome/PageNav.svelte";
	import SearchModal from "$lib/chrome/SearchModal.svelte";
	import Sidebar from "$lib/chrome/Sidebar.svelte";
	import TopBar from "$lib/chrome/TopBar.svelte";
	import { setPageTitleContext } from "$lib/pageTitle";
	import { availableSections, site, splitPath } from "$lib/site";
	import type { Section } from "$lib/types";

	let { children } = $props();

	// `page.data` comes from the generated `+page.ts` (docs/source/architecture.md, C5); the error page
	// has none, so fall back to the URL to pick the section.
	let section: Section = $derived(
		page.data.section ??
			splitPath(page.url.pathname, base).section ??
			availableSections[0]?.id ??
			"guide"
	);
	let headings = $derived(page.data.headings ?? null);
	let title = $derived(page.data.title ?? headings?.title ?? "");
	let documentTitle = $derived(
		page.error
			? `${page.status === 404 ? "Page not found" : "Error"} · ${site.title} · Cerulean Docs`
			: title
				? `${title} · ${site.title} · Cerulean Docs`
				: `${site.title} · Cerulean Docs`
	);
	// The page's own H1 carries the title row; pages without one get it from the layout.
	let contentHasH1 = $derived(headings?.depth === 1);
	let isDocPage = $derived(!page.error && !!page.data.section);

	setPageTitleContext({
		get local() {
			return contentHasH1 && headings ? headings.local : null;
		},
		actions: titleActions,
	});

	let drawerOpen = $state(false);
	let searchOpen = $state(false);

	afterNavigate(() => {
		drawerOpen = false;
	});

	/** Opens search on `/` and Cmd/Ctrl-K, unless the user is typing somewhere. */
	function onKeydown(event: KeyboardEvent) {
		if (searchOpen) return;
		const target = event.target as HTMLElement | null;
		const typing =
			!!target &&
			(target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
		const isCmdK = event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey);
		const isSlash = event.key === "/" && !typing && !event.metaKey && !event.ctrlKey;
		if (isCmdK || isSlash) {
			event.preventDefault();
			searchOpen = true;
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

<svelte:head>
	<title>{documentTitle}</title>
	{#if site.description}
		<meta name="description" content={site.description} />
	{/if}
	<meta property="og:site_name" content="Cerulean Docs" />
	<meta property="og:title" content={documentTitle} />
</svelte:head>

{#snippet titleActions()}
	{#if page.data.mdUrl}
		<CopyLLMTxtMenu mdUrl={page.data.mdUrl} />
	{/if}
{/snippet}

<a class="skip-link" href="#main-content">Skip to content</a>

<TopBar
	{section}
	menuOpen={drawerOpen}
	onMenu={() => (drawerOpen = true)}
	onSearch={() => (searchOpen = true)}
/>

<div class="docs-shell">
	<Sidebar {section} open={drawerOpen} onClose={() => (drawerOpen = false)} />

	<main id="main-content" class="docs-main" tabindex="-1">
		<article class="doc-content" data-pagefind-body={isDocPage ? "" : undefined}>
			{#if isDocPage}
				<!-- the section filter for search; `data-pagefind-ignore` keeps its text out of excerpts -->
				<span hidden data-pagefind-filter="section" data-pagefind-ignore>{section}</span>
			{/if}
			{#if isDocPage && !contentHasH1 && title}
				<div class="doc-title-row">
					<h1 class="doc-heading">{title}</h1>
					<div class="doc-title-actions" data-pagefind-ignore>
						{@render titleActions()}
					</div>
				</div>
			{/if}
			{@render children?.()}
		</article>

		{#if isDocPage}
			<footer class="doc-footer">
				{#if page.data.editUrl}
					<EditOnGithub href={page.data.editUrl} classNames="narrow-only" />
				{/if}
				<PageNav {section} />
			</footer>
		{/if}
	</main>

	<aside class="docs-rail" aria-label="Page tools">
		{#if isDocPage}
			<div class="docs-rail-inner">
				<OnThisPage {headings} />
				{#if page.data.editUrl}
					<EditOnGithub href={page.data.editUrl} />
				{/if}
			</div>
		{/if}
	</aside>
</div>

<SearchModal open={searchOpen} onClose={() => (searchOpen = false)} />
