<script lang="ts">
	import { onMount } from "svelte";
	import { base } from "$app/paths";
	import Dropdown from "../Dropdown.svelte";
	import DropdownEntry from "../DropdownEntry.svelte";
	import { availableSections, site } from "../site";
	import type { ProjectsManifest } from "../types";
	import { fetchProjects } from "./manifests";

	let projects: ProjectsManifest | null = $state(null);

	onMount(async () => {
		projects = await fetchProjects();
	});
</script>

<Dropdown
	classNames="project-switcher"
	btnClassNames="switcher-button"
	btnLabel={site.title}
	ariaLabel="Project: {site.title}. Switch project"
>
	{#snippet menu()}
		{#if projects?.length}
			{#each projects as project (project.name)}
				<DropdownEntry
					href="/{encodeURIComponent(project.name)}/"
					label={project.title || project.name}
					description={project.description}
					current={project.name === site.project}
				/>
			{/each}
			<DropdownEntry classNames="dropdown-entry-footer" href="/" label="All projects" />
		{:else}
			<!-- The Worker's project list never loads in `doc-builder preview`: offer this project only. -->
			<DropdownEntry
				href="{base}/{availableSections[0]?.id ?? 'guide'}/"
				label={site.title}
				description={site.description}
				current
			/>
		{/if}
	{/snippet}
</Dropdown>
