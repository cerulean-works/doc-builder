<script lang="ts">
	import { onMount } from "svelte";

	interface Props {
		/** base64 of the URI-encoded diagram source */
		code?: string;
		classNames?: string;
	}

	let { code = "", classNames = "" }: Props = $props();

	let svgMarkup = $state("");
	let error = $state("");
	let renderCount = 0;
	const chartId = `mermaid-${Math.random().toString(36).slice(2, 11)}`;

	/** Mermaid needs literal colors, so read the current theme's tokens from `:root`. */
	function themeVariables() {
		const style = getComputedStyle(document.documentElement);
		const token = (name: string) => style.getPropertyValue(name).trim();
		const dark = document.documentElement.classList.contains("dark-theme");
		return {
			darkMode: dark,
			background: token("--c-paper"),
			fontFamily: token("--font-ui") || "sans-serif",
			fontSize: "14px",
			primaryColor: token("--c-surface"),
			primaryTextColor: token("--c-ink"),
			primaryBorderColor: token("--c-muted"),
			secondaryColor: token("--c-paper"),
			tertiaryColor: token("--c-paper"),
			lineColor: token("--c-muted"),
			textColor: token("--c-ink"),
			mainBkg: token("--c-surface"),
			nodeBorder: token("--c-muted"),
			clusterBkg: token("--c-paper"),
			clusterBorder: token("--c-rule"),
			edgeLabelBackground: token("--c-paper"),
			noteBkgColor: token("--c-surface"),
			noteTextColor: token("--c-ink"),
			noteBorderColor: token("--c-rule"),
		};
	}

	async function render() {
		const current = ++renderCount;
		const { default: mermaid } = await import("mermaid");
		mermaid.initialize({
			startOnLoad: false,
			theme: "base",
			themeVariables: themeVariables(),
			securityLevel: "strict",
			fontFamily: "inherit",
		});
		try {
			const { svg } = await mermaid.render(`${chartId}-${current}`, decodeURIComponent(atob(code)));
			if (current === renderCount) {
				svgMarkup = svg;
				error = "";
			}
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	onMount(() => {
		render();
		// Re-render when the Daylight/Evening theme changes.
		const observer = new MutationObserver(() => render());
		observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
		return () => observer.disconnect();
	});
</script>

<figure class="mermaid-chart {classNames}">
	<!-- mermaid output, rendered with securityLevel "strict" -->
	<div>{@html svgMarkup}</div>
	{#if error}
		<figcaption class="mermaid-error">
			<strong>Could not render this diagram.</strong>
			<code>{error}</code>
		</figcaption>
	{/if}
</figure>
