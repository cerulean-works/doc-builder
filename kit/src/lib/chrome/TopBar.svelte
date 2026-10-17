<script lang="ts">
	import { onMount } from "svelte";
	import { base } from "$app/paths";
	import IconGithub from "../IconGithub.svelte";
	import { availableSections, site } from "../site";
	import type { Section } from "../types";
	import LogoMark from "./LogoMark.svelte";
	import ProjectSwitcher from "./ProjectSwitcher.svelte";
	import SectionTabs from "./SectionTabs.svelte";
	import ThemeToggle from "./ThemeToggle.svelte";
	import VersionSwitcher from "./VersionSwitcher.svelte";
	import { fetchProjects } from "./manifests";

	interface Props {
		section: Section;
		menuOpen: boolean;
		onMenu: () => void;
		onSearch: () => void;
	}

	let { section, menuOpen, onMenu, onSearch }: Props = $props();

	// The brand leads to the Worker's project list, or to this project when there is none
	// (`doc-builder preview`).
	let brandHref = $state(`${base}/${availableSections[0]?.id ?? "guide"}/`);

	onMount(async () => {
		if (await fetchProjects()) brandHref = "/";
	});
</script>

<header class="topbar">
	<button
		class="icon-button menu-button"
		type="button"
		aria-label="Open navigation"
		aria-expanded={menuOpen}
		onclick={onMenu}
	>
		<svg
			viewBox="0 0 24 24"
			width="20"
			height="20"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			aria-hidden="true"
		>
			<path d="M3 6h18M3 12h18M3 18h18" />
		</svg>
	</button>

	<a class="brand" href={brandHref}>
		<LogoMark />
		<span class="brand-name">Cerulean <span class="brand-suffix">Docs</span></span>
	</a>

	<div class="topbar-switchers wide-only">
		<span class="topbar-divider" aria-hidden="true">/</span>
		<ProjectSwitcher />
		<VersionSwitcher />
	</div>

	<div class="topbar-nav wide-only">
		<SectionTabs {section} />
	</div>

	<div class="topbar-actions">
		<button
			class="search-trigger"
			type="button"
			onclick={onSearch}
			aria-label="Search documentation"
		>
			<svg
				viewBox="0 0 24 24"
				width="16"
				height="16"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				aria-hidden="true"
			>
				<circle cx="11" cy="11" r="7" />
				<path d="m20 20-4-4" />
			</svg>
			<span class="search-trigger-label">Search documentation</span>
			<kbd>/</kbd>
		</button>
		<ThemeToggle />
		{#if site.repo}
			<a
				class="icon-button github-link"
				href="https://github.com/{site.repo}"
				aria-label="{site.repo} on GitHub"
				title="{site.repo} on GitHub"
			>
				<IconGithub />
			</a>
		{/if}
	</div>
</header>
