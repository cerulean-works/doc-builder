<script lang="ts">
	interface Props {
		version: string;
		children?: import("svelte").Snippet;
	}

	let { version, children }: Props = $props();
</script>

<blockquote class="callout version-note note">
	<p class="callout-title">Added in {version}</p>
	{@render children?.()}
</blockquote>
