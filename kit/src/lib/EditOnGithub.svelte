<script lang="ts">
	// Rendered by the layout from `page.data.editUrl` (docs/source/architecture.md, C5).
	import IconGithub from "./IconGithub.svelte";

	interface Props {
		href: string;
		classNames?: string;
	}

	let { href, classNames = "" }: Props = $props();
</script>

<a class="edit-on-github {classNames}" {href} target="_blank" rel="noopener">
	<IconGithub />
	<span>Edit on GitHub</span>
</a>
