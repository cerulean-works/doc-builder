<script lang="ts">
	import { untrack } from "svelte";
	import { page } from "$app/state";
	import IconCaret from "../IconCaret.svelte";
	import { containsPath, withTrailingSlash } from "../site";
	import type { TocEntry } from "../types";
	import TocTree from "./TocTree.svelte";

	interface Props {
		entries: TocEntry[];
		depth?: number;
	}

	let { entries, depth = 0 }: Props = $props();

	let pathname = $derived(withTrailingSlash(page.url.pathname));

	// Groups follow `isExpanded` (default: expanded), and always open to reveal the current page.
	let collapsed: Record<number, boolean> = $state(
		untrack(() =>
			Object.fromEntries(
				entries.map((entry, index) => [
					index,
					entry.isExpanded === false && !containsPath(entry, page.url.pathname),
				])
			)
		)
	);

	$effect(() => {
		entries.forEach((entry, index) => {
			if (entry.sections && containsPath(entry, pathname)) collapsed[index] = false;
		});
	});

	const isCurrent = (entry: TocEntry) => !!entry.url && withTrailingSlash(entry.url) === pathname;
</script>

<ul class="toc-list" class:toc-root={depth === 0}>
	{#each entries as entry, index (index)}
		<li class="toc-item" class:toc-group={!!entry.sections?.length}>
			{#if entry.sections?.length}
				<div class="toc-group-header" class:is-current={isCurrent(entry)}>
					{#if entry.url}
						<a
							class="toc-group-title"
							href={entry.url}
							aria-current={isCurrent(entry) ? "page" : undefined}>{entry.title}</a
						>
						<button
							type="button"
							class="toc-toggle"
							aria-expanded={!collapsed[index]}
							aria-label="Show pages under {entry.title}"
							onclick={() => (collapsed[index] = !collapsed[index])}
						>
							<IconCaret classNames={collapsed[index] ? "-rotate-90" : ""} />
						</button>
					{:else}
						<button
							type="button"
							class="toc-group-title"
							aria-expanded={!collapsed[index]}
							onclick={() => (collapsed[index] = !collapsed[index])}
						>
							<span>{entry.title}</span>
							<IconCaret classNames="toc-caret {collapsed[index] ? '-rotate-90' : ''}" />
						</button>
					{/if}
				</div>
				<div class="toc-children" hidden={collapsed[index]}>
					<TocTree entries={entry.sections} depth={depth + 1} />
				</div>
			{:else if entry.url}
				<a
					class="toc-link"
					class:is-current={isCurrent(entry)}
					href={entry.url}
					aria-current={isCurrent(entry) ? "page" : undefined}>{entry.title}</a
				>
			{:else}
				<span class="toc-link">{entry.title}</span>
			{/if}
		</li>
	{/each}
</ul>
