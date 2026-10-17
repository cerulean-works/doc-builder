<script lang="ts">
	import { base } from "$app/paths";
	import { page } from "$app/state";
	import { availableSections, site, versionLabel } from "$lib/site";

	let notFound = $derived(page.status === 404);
</script>

<div class="error-page">
	<p class="error-status">{page.status}</p>
	<h1 class="doc-heading">{notFound ? "Page not found" : "Something went wrong"}</h1>
	{#if notFound}
		<p>
			There is no page at <code>{page.url.pathname}</code> in the {site.title} documentation for
			{versionLabel(site.version)}. It may have moved, or it may only exist in another version.
		</p>
	{:else}
		<p>{page.error?.message ?? "The page could not be loaded."}</p>
	{/if}
	<ul class="error-links">
		{#each availableSections as { id, label } (id)}
			<li><a href="{base}/{id}/">{label}</a></li>
		{/each}
		<li><a href="/{site.project}/">Latest version</a></li>
	</ul>
</div>
