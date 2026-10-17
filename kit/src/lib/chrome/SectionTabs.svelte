<script lang="ts">
	import { base } from "$app/paths";
	import { availableSections } from "../site";
	import type { Section } from "../types";

	interface Props {
		section: Section;
	}

	let { section }: Props = $props();
</script>

<nav class="section-tabs" aria-label="Sections">
	{#each availableSections as { id, label } (id)}
		<a class="section-tab" href="{base}/{id}/" aria-current={id === section ? "true" : undefined}
			>{label}</a
		>
	{/each}
</nav>
