<script lang="ts">
	import { selectedTabs } from "./stores";

	interface Props {
		id: string;
		option: string;
		children?: import("svelte").Snippet;
	}

	let { id, option, children }: Props = $props();
</script>

<!-- Every option is in the server-rendered HTML (and the search index); inactive ones are hidden. -->
<div role="tabpanel" aria-label={option} hidden={$selectedTabs[id] !== option}>
	{@render children?.()}
</div>
