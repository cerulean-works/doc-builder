<script lang="ts">
	import { onMount, untrack } from "svelte";
	import { selectedTabs } from "./stores";
	import { getQueryParamValue, updateQueryParamAndReplaceHistory } from "./utils";

	interface Props {
		id: string;
		options: string[];
		children?: import("svelte").Snippet;
	}

	let { id, options, children }: Props = $props();

	// the first option is selected until the user (or the query string) picks another
	untrack(() => ($selectedTabs[id] = options[0]));

	function select(option: string) {
		$selectedTabs[id] = option;
		updateQueryParamAndReplaceHistory(id, option);
	}

	function onKeydown(event: KeyboardEvent, index: number) {
		const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
		if (!delta) return;
		event.preventDefault();
		const next = (index + delta + options.length) % options.length;
		select(options[next]);
		const tabList = (event.currentTarget as HTMLElement).parentElement;
		tabList?.querySelectorAll<HTMLButtonElement>("[role=tab]")[next]?.focus();
	}

	onMount(() => {
		const fromQuery = getQueryParamValue(id);
		if (fromQuery && options.includes(fromQuery)) {
			$selectedTabs[id] = fromQuery;
		}
	});
</script>

<div class="doc-tabs">
	<div class="doc-tabs-list" role="tablist">
		{#each options as option, index (option)}
			<button
				type="button"
				role="tab"
				class="doc-tab"
				aria-selected={$selectedTabs[id] === option}
				tabindex={$selectedTabs[id] === option ? 0 : -1}
				onclick={() => select(option)}
				onkeydown={(event) => onKeydown(event, index)}
			>
				{option}
			</button>
		{/each}
	</div>
	<div class="doc-tabs-panels">
		{@render children?.()}
	</div>
</div>
