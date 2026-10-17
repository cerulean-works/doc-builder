<script lang="ts">
	import type { Snippet } from "svelte";
	import DropdownMenu from "./DropdownMenu.svelte";
	import IconChevronUpDown from "./IconChevronUpDown.svelte";

	interface Props {
		classNames?: string;
		btnClassNames?: string;
		btnLabel?: string;
		/** accessible name of the button when its visible label isn't descriptive enough */
		ariaLabel?: string;
		forceMenuAlignement?: "left" | "right" | undefined;
		menuClassNames?: string;
		withBtnCaret?: boolean;
		button?: Snippet;
		menu?: Snippet;
	}

	let {
		classNames = "",
		btnClassNames = "",
		btnLabel = "",
		ariaLabel = undefined,
		forceMenuAlignement = undefined,
		menuClassNames = "",
		withBtnCaret = true,
		button,
		menu,
	}: Props = $props();

	let element: HTMLElement | undefined = $state(undefined);
	let isOpen = $state(false);

	function onClose() {
		isOpen = false;
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === "Escape" && isOpen) {
			isOpen = false;
			element?.querySelector("button")?.focus();
		}
	}
</script>

<div class="dropdown {classNames}" bind:this={element} onkeydown={onKeydown} role="presentation">
	<button
		class="dropdown-button {btnClassNames}"
		onclick={() => (isOpen = !isOpen)}
		type="button"
		aria-haspopup="menu"
		aria-expanded={isOpen}
		aria-label={ariaLabel}
	>
		{#if button}
			{@render button()}
		{:else}
			<span>{btnLabel}</span>
		{/if}
		{#if withBtnCaret}
			<IconChevronUpDown classNames="dropdown-caret" />
		{/if}
	</button>
	{#if isOpen}
		<DropdownMenu
			classNames={menuClassNames}
			dropdownElement={element}
			forceAlignement={forceMenuAlignement}
			{onClose}
		>
			{@render menu?.()}
		</DropdownMenu>
	{/if}
</div>
