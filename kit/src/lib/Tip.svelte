<script lang="ts">
	interface Props {
		warning?: boolean;
		children?: import("svelte").Snippet;
	}

	let { warning = false, children }: Props = $props();
</script>

<blockquote class="callout {warning ? 'warning' : 'tip'}">
	{@render children?.()}
</blockquote>
