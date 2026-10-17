<script lang="ts">
	import { onMount } from "svelte";
	import { base } from "$app/paths";
	import { page } from "$app/state";
	import Dropdown from "../Dropdown.svelte";
	import DropdownEntry from "../DropdownEntry.svelte";
	import { site, versionLabel } from "../site";
	import type { VersionsManifest } from "../types";
	import { fetchVersions } from "./manifests";

	// Until the Worker's version list loads (it never does in `doc-builder preview`), the menu
	// holds just this version.
	const fallback: VersionsManifest = {
		default: site.version,
		versions: [{ version: site.version }],
	};

	let manifest = $state<VersionsManifest | null>(null);
	let shown = $derived(manifest?.versions.length ? manifest : fallback);

	onMount(async () => {
		manifest = await fetchVersions(site.project);
	});

	/**
	 * Each version is its own SvelteKit app, so switching is a full navigation to the same page
	 * under the other version's base path (`/<p>/<v2>/<section>/<rest>`). Links outside this
	 * build's base path are external to SvelteKit, so the browser performs that navigation.
	 */
	function hrefFor(version: string) {
		const rest = page.url.pathname.startsWith(base) ? page.url.pathname.slice(base.length) : "/";
		return `/${site.project}/${version}${rest}`;
	}
</script>

<Dropdown
	classNames="version-switcher"
	btnClassNames="switcher-button"
	btnLabel={versionLabel(site.version)}
	ariaLabel="Version: {versionLabel(site.version)}. Switch version"
>
	{#snippet menu()}
		{#each shown.versions as { version } (version)}
			<DropdownEntry
				href={hrefFor(version)}
				label={versionLabel(version)}
				description={manifest && version === manifest.default ? "Default" : undefined}
				current={version === site.version}
			/>
		{/each}
	{/snippet}
</Dropdown>
