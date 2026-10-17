<script lang="ts">
	import { tick } from "svelte";
	import { site } from "../site";
	import type { Section } from "../types";
	import ProjectSwitcher from "./ProjectSwitcher.svelte";
	import SectionTabs from "./SectionTabs.svelte";
	import TocTree from "./TocTree.svelte";
	import VersionSwitcher from "./VersionSwitcher.svelte";

	interface Props {
		section: Section;
		/** drawer state on narrow screens; on wide screens the sidebar is always shown */
		open: boolean;
		onClose: () => void;
	}

	let { section, open, onClose }: Props = $props();

	let element: HTMLElement | undefined = $state();

	$effect(() => {
		if (open) {
			tick().then(() => element?.querySelector<HTMLElement>("a, button")?.focus());
		}
	});

	function onKeydown(event: KeyboardEvent) {
		if (open && event.key === "Escape") onClose();
	}
</script>

<svelte:window onkeydown={onKeydown} />

{#if open}
	<button class="drawer-backdrop" type="button" aria-label="Close navigation" onclick={onClose}
	></button>
{/if}

<aside class="docs-sidebar" class:open bind:this={element} aria-label="Documentation">
	<div class="drawer-only drawer-controls">
		<SectionTabs {section} />
		<div class="drawer-switchers">
			<ProjectSwitcher />
			<VersionSwitcher />
		</div>
	</div>
	<nav class="sidebar-nav" aria-label="{section === 'guide' ? 'Guide' : 'Reference'} pages">
		<TocTree entries={site.toctree[section] ?? []} />
	</nav>
</aside>
