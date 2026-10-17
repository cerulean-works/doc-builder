<script lang="ts">
	import { onMount } from "svelte";
	import { syncTheme, theme, toggleTheme } from "../theme.svelte";

	onMount(syncTheme);

	let label = $derived(theme.dark ? "Switch to light mode" : "Switch to dark mode");
</script>

<!-- Icons are switched by the `:root.dark-theme` class so the right one shows before hydration. -->
<button
	class="icon-button theme-toggle"
	type="button"
	aria-label={label}
	title={label}
	onclick={toggleTheme}
>
	<svg
		class="theme-sun"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.5"
		stroke-linecap="round"
		aria-hidden="true"
	>
		<circle cx="12" cy="12" r="4" />
		<path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" />
	</svg>
	<svg
		class="theme-moon"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.5"
		stroke-linecap="round"
		stroke-linejoin="round"
		aria-hidden="true"
	>
		<path d="M20.5 13.2A8.5 8.5 0 0 1 10.8 3.5a8.5 8.5 0 1 0 9.7 9.7Z" />
	</svg>
</button>

<style>
	.theme-toggle svg {
		width: 18px;
		height: 18px;
	}

	.theme-sun,
	:global(.dark-theme) .theme-moon {
		display: none;
	}

	:global(.dark-theme) .theme-sun {
		display: block;
	}
</style>
