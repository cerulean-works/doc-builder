<script lang="ts">
	import { onMount } from "svelte";

	import IconCopyLink from "./IconCopyLink.svelte";

	interface Props {
		anchor: string;
		children?: import("svelte").Snippet;
	}

	let { anchor, children }: Props = $props();

	let isTarget = $state(false);

	function onHashChange() {
		isTarget = window.location.hash.substring(1) === anchor;
	}

	onMount(onHashChange);
</script>

<svelte:window onhashchange={onHashChange} />

<div class="example-code-block" class:is-target={isTarget}>
	<a id={anchor} class="header-link" href={`#${anchor}`} aria-label="Link to this example"
		><IconCopyLink /></a
	>
	{@render children?.()}
</div>
