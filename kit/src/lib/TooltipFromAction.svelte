<script lang="ts">
	interface Props {
		txt: string;
		x: number;
		y: number;
		id: string;
	}

	let { txt, x, y, id }: Props = $props();
</script>

{#if txt}
	<div
		class="docstring-tooltip"
		class:wide={txt.length > 1000}
		style="top: {y + 15}px; left: {x + 15}px;"
		{id}
	>
		{@html txt}
	</div>
{/if}
