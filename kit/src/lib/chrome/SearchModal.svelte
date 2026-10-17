<script lang="ts">
	import { tick, untrack } from "svelte";
	import { base } from "$app/paths";
	import { goto } from "$app/navigation";
	import { SECTIONS } from "../site";
	import type { Section } from "../types";

	interface Props {
		open: boolean;
		onClose: () => void;
	}

	let { open, onClose }: Props = $props();

	/** The subset of the Pagefind JS API used here (https://pagefind.app/docs/api/). */
	interface PagefindResultData {
		url: string;
		excerpt: string;
		meta: { title?: string };
		filters: Record<string, string[]>;
	}
	interface Pagefind {
		options: (options: Record<string, unknown>) => Promise<void>;
		init: () => Promise<void>;
		debouncedSearch: (
			term: string,
			options?: { filters?: Record<string, string> },
			debounceMs?: number
		) => Promise<{ results: { data: () => Promise<PagefindResultData> }[] } | null>;
	}

	let pagefind: Promise<Pagefind | null> | undefined;

	/** Pagefind is generated next to the build (`pagefind --site build`), so it only exists there. */
	function loadPagefind(): Promise<Pagefind | null> {
		pagefind ??= (async () => {
			try {
				const module: Pagefind = await import(/* @vite-ignore */ `${base}/pagefind/pagefind.js`);
				await module.options({ baseUrl: `${base}/` });
				await module.init();
				return module;
			} catch (error) {
				console.warn("Search index unavailable", error);
				// let the next open retry, e.g. after a transient network error
				pagefind = undefined;
				return null;
			}
		})();
		return pagefind;
	}

	let query = $state("");
	let filter: Section | "all" = $state("all");
	let results: PagefindResultData[] = $state([]);
	let status: "idle" | "loading" | "ready" | "unavailable" = $state("idle");
	let selected = $state(0);
	let input: HTMLInputElement | undefined = $state();
	let dialog: HTMLDialogElement | undefined = $state();
	let resultsList: HTMLElement | undefined = $state();

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) {
			dialog.showModal();
			tick().then(() => input?.select());
			loadPagefind().then((module) => {
				if (!module) status = "unavailable";
				else if (status === "unavailable") status = "idle";
			});
		} else if (!open && dialog.open) {
			dialog.close();
		}
	});

	// search as the query or filter changes
	$effect(() => {
		const term = query.trim();
		const filters = filter === "all" ? undefined : { section: filter };
		const unavailable = untrack(() => status === "unavailable");
		if (!open || !term) {
			results = [];
			if (!unavailable) status = "idle";
			return;
		}
		let cancelled = false;
		if (!unavailable) status = "loading";
		loadPagefind().then(async (module) => {
			if (!module || cancelled) return;
			const search = await module.debouncedSearch(term, { filters }, 150);
			if (!search || cancelled) return; // superseded by a newer search
			const data = await Promise.all(search.results.slice(0, 12).map((result) => result.data()));
			if (cancelled) return;
			results = data;
			selected = 0;
			status = "ready";
		});
		return () => {
			cancelled = true;
		};
	});

	function sectionOf(result: PagefindResultData) {
		const id = result.filters?.section?.[0];
		return SECTIONS.find((section) => section.id === id)?.label;
	}

	async function openResult(result: PagefindResultData) {
		onClose();
		await goto(result.url);
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === "ArrowDown" || event.key === "ArrowUp") {
			if (!results.length) return;
			event.preventDefault();
			const delta = event.key === "ArrowDown" ? 1 : -1;
			selected = (selected + delta + results.length) % results.length;
			tick().then(() =>
				resultsList
					?.querySelector<HTMLElement>(`[data-index="${selected}"]`)
					?.scrollIntoView({ block: "nearest" })
			);
		} else if (event.key === "Enter" && event.target === input && results[selected]) {
			event.preventDefault();
			openResult(results[selected]);
		}
	}
</script>

<dialog
	class="search-dialog"
	bind:this={dialog}
	onclose={onClose}
	onclick={(event) => event.target === dialog && onClose()}
	aria-label="Search documentation"
>
	<div class="search-panel" role="presentation" onkeydown={onKeydown}>
		<div class="search-input-row">
			<svg
				viewBox="0 0 24 24"
				width="18"
				height="18"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				aria-hidden="true"
			>
				<circle cx="11" cy="11" r="7" />
				<path d="m20 20-4-4" />
			</svg>
			<input
				bind:this={input}
				bind:value={query}
				type="search"
				placeholder="Search documentation"
				aria-label="Search documentation"
				aria-controls="search-results"
				aria-activedescendant={results.length ? `search-result-${selected}` : undefined}
				autocomplete="off"
				spellcheck="false"
			/>
			<button type="button" class="search-close" onclick={onClose}>Esc</button>
		</div>
		<div class="search-filters" role="group" aria-label="Filter by section">
			{#each [{ id: "all", label: "All" }, ...SECTIONS] as chip (chip.id)}
				<button
					type="button"
					class="search-chip"
					aria-pressed={filter === chip.id}
					onclick={() => {
						filter = chip.id as Section | "all";
						input?.focus();
					}}>{chip.label}</button
				>
			{/each}
		</div>
		<div class="search-results" bind:this={resultsList}>
			{#if status === "unavailable"}
				<p class="search-message">
					Search isn't available here. The index is generated by <code>pnpm run build</code>.
				</p>
			{:else if !query.trim()}
				<p class="search-message">Type to search the documentation.</p>
			{:else if status === "ready" && !results.length}
				<p class="search-message">No results for “{query.trim()}”.</p>
			{:else}
				<ul id="search-results" role="listbox" aria-label="Search results">
					{#each results as result, index (result.url)}
						<li
							id="search-result-{index}"
							role="option"
							aria-selected={index === selected}
							data-index={index}
						>
							<a
								href={result.url}
								class="search-result"
								class:is-selected={index === selected}
								tabindex="-1"
								onmousemove={() => (selected = index)}
								onclick={(event) => {
									event.preventDefault();
									openResult(result);
								}}
							>
								<span class="search-result-title">
									{result.meta.title ?? result.url}
									{#if sectionOf(result)}
										<span class="search-result-section">{sectionOf(result)}</span>
									{/if}
								</span>
								<!-- Pagefind escapes page text and only adds <mark> around matches -->
								<span class="search-result-excerpt">{@html result.excerpt}</span>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
		<div class="search-footer" aria-hidden="true">
			<span><kbd>↑</kbd><kbd>↓</kbd> to navigate</span>
			<span><kbd>Enter</kbd> to open</span>
			<span><kbd>Esc</kbd> to close</span>
		</div>
	</div>
</dialog>
