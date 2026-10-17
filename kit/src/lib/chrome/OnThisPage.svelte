<script lang="ts">
	import type { HeadingNode } from "../types";

	interface Props {
		headings: HeadingNode | null | undefined;
	}

	let { headings }: Props = $props();

	/** H2s and H3s: the children of the page's H1 (or the top-level heading if there is no H1). */
	let items = $derived.by(() => {
		if (!headings) return [];
		const top = headings.depth === 1 ? (headings.sections ?? []) : [headings];
		return top
			.filter((node) => node.depth <= 3)
			.flatMap((node) => [node, ...(node.sections ?? []).filter((child) => child.depth === 3)]);
	});

	let activeId: string | null = $state(null);

	/** The active item is the last heading scrolled past the top bar. */
	function updateActive() {
		const offset = 96;
		let current: string | null = items[0]?.local ?? null;
		for (const item of items) {
			const element = document.getElementById(item.local);
			if (element && element.getBoundingClientRect().top <= offset) current = item.local;
		}
		const atBottom =
			window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
		if (atBottom && items.length) current = items[items.length - 1].local;
		activeId = current;
	}

	$effect(() => {
		// re-run when the page (and its headings) change
		void items;
		// a handful of layout reads per scroll event; cheap enough without frame throttling
		updateActive();
		window.addEventListener("scroll", updateActive, { passive: true });
		window.addEventListener("resize", updateActive, { passive: true });
		return () => {
			window.removeEventListener("scroll", updateActive);
			window.removeEventListener("resize", updateActive);
		};
	});
</script>

{#if items.length}
	<nav class="on-this-page" aria-labelledby="on-this-page-title">
		<p class="rail-title" id="on-this-page-title">On this page</p>
		<ul>
			{#each items as item, index (index)}
				<li class:depth-3={item.depth === 3}>
					<a
						href="#{item.local}"
						class:is-active={activeId === item.local}
						aria-current={activeId === item.local ? "location" : undefined}>{item.title}</a
					>
				</li>
			{/each}
		</ul>
	</nav>
{/if}
