<script lang="ts">
	import IconCopyLink from "./IconCopyLink.svelte";
	import { getPageTitleContext } from "./pageTitle";
	import { escapeHtml } from "./utils";

	interface Props {
		title: string;
		local: string;
		headingTag: string;
	}

	let { title, local, headingTag }: Props = $props();

	const pageTitle = getPageTitleContext();
	let tag = $derived(/^h[1-6]$/.test(headingTag) ? headingTag : "h6");
	let withActions = $derived(tag === "h1" && !!pageTitle && pageTitle.local === local);
</script>

{#snippet heading()}
	<svelte:element this={tag} class="doc-heading" id={local}>
		<span>{@html escapeHtml(title)}</span>
		<a class="header-link" href="#{local}" aria-label="Link to this section" data-pagefind-ignore
			><IconCopyLink /></a
		>
	</svelte:element>
{/snippet}

{#if withActions && pageTitle}
	<div class="doc-title-row">
		{@render heading()}
		<div class="doc-title-actions" data-pagefind-ignore>
			{@render pageTitle.actions()}
		</div>
	</div>
{:else}
	{@render heading()}
{/if}
