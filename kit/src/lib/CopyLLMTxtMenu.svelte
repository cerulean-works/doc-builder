<script lang="ts">
	import { onDestroy } from "svelte";
	import { copyToClipboard } from "./copyToClipboard";
	import DropdownMenu from "./DropdownMenu.svelte";
	import IconAnthropic from "./IconAnthropic.svelte";
	import IconArrowUpRight from "./IconArrowUpRight.svelte";
	import IconCaret from "./IconCaret.svelte";
	import IconCode from "./IconCode.svelte";
	import IconCopy from "./IconCopy.svelte";
	import IconOpenAI from "./IconOpenAI.svelte";

	interface Props {
		/** The page's Markdown export (`X.md` for a page at `X/`, docs/source/architecture.md C1). */
		mdUrl: string;
		label?: string;
	}

	let { mdUrl, label = "Copy page" }: Props = $props();

	let open = $state(false);
	let status: "idle" | "copied" | "failed" = $state("idle");
	let element: HTMLElement | undefined = $state();
	let resetTimeout: ReturnType<typeof setTimeout> | undefined;
	let markdown: Promise<string> | undefined;

	onDestroy(() => clearTimeout(resetTimeout));

	function fetchMarkdown(): Promise<string> {
		markdown ??= fetch(mdUrl, { headers: { Accept: "text/markdown, text/plain" } }).then(
			(response) => {
				if (!response.ok) throw new Error(`${response.status} fetching ${mdUrl}`);
				return response.text();
			}
		);
		// don't cache failures, so a retry can succeed
		markdown.catch(() => (markdown = undefined));
		return markdown;
	}

	async function copyMarkdown() {
		open = false;
		try {
			const text = await fetchMarkdown();
			try {
				await navigator.clipboard.writeText(text);
			} catch {
				copyToClipboard(text);
			}
			status = "copied";
		} catch (error) {
			console.error("Unable to copy the page as Markdown", error);
			status = "failed";
		}
		clearTimeout(resetTimeout);
		resetTimeout = setTimeout(() => (status = "idle"), 2000);
	}

	function absoluteUrl(path: string) {
		return new URL(path, window.location.href).href;
	}

	function askUrl(target: "chatgpt" | "claude") {
		const prompt = encodeURIComponent(
			`Read from ${absoluteUrl(mdUrl)} so I can ask questions about it.`
		);
		return target === "chatgpt"
			? `https://chatgpt.com/?hints=search&q=${prompt}`
			: `https://claude.ai/new?q=${prompt}`;
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === "Escape" && open) {
			open = false;
			element?.querySelector<HTMLElement>(".copy-page-toggle")?.focus();
		}
	}
</script>

<div class="copy-page" bind:this={element} onkeydown={onKeydown} role="presentation">
	<div class="copy-page-buttons">
		<button type="button" class="copy-page-main" onclick={copyMarkdown}>
			<IconCopy />
			<span aria-live="polite"
				>{status === "copied" ? "Copied" : status === "failed" ? "Copy failed" : label}</span
			>
		</button>
		<button
			type="button"
			class="copy-page-toggle"
			onclick={() => (open = !open)}
			aria-haspopup="menu"
			aria-expanded={open}
			aria-label="More page actions"
		>
			<IconCaret classNames={open ? "rotate-180" : ""} />
		</button>
	</div>

	{#if open}
		<DropdownMenu
			dropdownElement={element}
			forceAlignement="right"
			onClose={() => (open = false)}
			classNames="copy-page-menu"
		>
			<li role="none">
				<button type="button" role="menuitem" class="dropdown-entry" onclick={copyMarkdown}>
					<span class="dropdown-entry-icon"><IconCopy /></span>
					<span>
						<span class="dropdown-entry-label">{label}</span>
						<span class="dropdown-entry-description">Copy this page as Markdown for LLMs</span>
					</span>
				</button>
			</li>
			<li role="none">
				<a
					role="menuitem"
					class="dropdown-entry"
					href={mdUrl}
					target="_blank"
					rel="noopener"
					onclick={() => (open = false)}
				>
					<span class="dropdown-entry-icon"><IconCode /></span>
					<span>
						<span class="dropdown-entry-label">View as Markdown <IconArrowUpRight /></span>
						<span class="dropdown-entry-description">Open this page as plain text</span>
					</span>
				</a>
			</li>
			<li role="none">
				<a
					role="menuitem"
					class="dropdown-entry"
					href={askUrl("chatgpt")}
					target="_blank"
					rel="noopener noreferrer"
					onclick={() => (open = false)}
				>
					<span class="dropdown-entry-icon"><IconOpenAI /></span>
					<span>
						<span class="dropdown-entry-label">Open in ChatGPT <IconArrowUpRight /></span>
						<span class="dropdown-entry-description">Ask questions about this page</span>
					</span>
				</a>
			</li>
			<li role="none">
				<a
					role="menuitem"
					class="dropdown-entry"
					href={askUrl("claude")}
					target="_blank"
					rel="noopener noreferrer"
					onclick={() => (open = false)}
				>
					<span class="dropdown-entry-icon"><IconAnthropic /></span>
					<span>
						<span class="dropdown-entry-label">Open in Claude <IconArrowUpRight /></span>
						<span class="dropdown-entry-description">Ask questions about this page</span>
					</span>
				</a>
			</li>
		</DropdownMenu>
	{/if}
</div>
