<script lang="ts">
	interface Props {
		version: string;
		children?: import("svelte").Snippet;
	}

	let { version, children }: Props = $props();
</script>

<blockquote class="callout version-note warning">
	<p class="callout-title">Deprecated in {version}</p>
	{@render children?.()}
</blockquote>
