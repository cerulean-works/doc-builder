<script lang="ts">
	interface Props {
		classNames?: string;
		href?: string | undefined;
		label?: string;
		/** marks the entry for the current page/version */
		current?: boolean;
		description?: string | undefined;
		onClick?: (e: MouseEvent) => void;
		targetBlank?: boolean;
		children?: import("svelte").Snippet;
	}

	let {
		classNames = "",
		href = undefined,
		label = "",
		current = false,
		description = undefined,
		onClick = () => {},
		targetBlank = false,
		children,
	}: Props = $props();
</script>

<li role="none">
	<a
		role="menuitem"
		class="dropdown-entry {classNames}"
		class:is-current={current}
		aria-current={current ? "true" : undefined}
		{href}
		onclick={onClick}
		target={targetBlank ? "_blank" : undefined}
		rel={targetBlank ? "noopener noreferrer" : undefined}
	>
		{#if children}
			{@render children()}
		{:else}
			<span class="dropdown-entry-label">{label}</span>
			{#if description}
				<span class="dropdown-entry-description">{description}</span>
			{/if}
		{/if}
	</a>
</li>
