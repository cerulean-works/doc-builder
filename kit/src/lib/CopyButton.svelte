<script lang="ts">
	import { onDestroy } from "svelte";
	import { copyToClipboard } from "./copyToClipboard";

	import IconCopy from "./IconCopy.svelte";

	interface Props {
		classNames?: string;
		label?: string;
		title?: string;
		/** base64 of the URI-encoded text, as emitted by the mdsvex code fence highlighter */
		value: string;
	}

	let { classNames = "", label = "Copy", title = "", value }: Props = $props();

	let isSuccess = $state(false);
	let timeout: ReturnType<typeof setTimeout> | undefined;

	onDestroy(() => clearTimeout(timeout));

	async function handleClick() {
		const text = decodeURIComponent(atob(value));
		try {
			await navigator.clipboard.writeText(text);
		} catch {
			copyToClipboard(text);
		}
		isSuccess = true;
		clearTimeout(timeout);
		timeout = setTimeout(() => (isSuccess = false), 1500);
	}
</script>

<button
	class="copy-button {classNames}"
	class:is-copied={isSuccess}
	onclick={handleClick}
	title={title || label}
	aria-label={label}
	type="button"
>
	<IconCopy />
	<span aria-live="polite">{isSuccess ? "Copied" : ""}</span>
</button>
