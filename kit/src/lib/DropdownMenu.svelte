<script lang="ts">
	import { onMount, untrack } from "svelte";

	type Alignement = "left" | "right";

	interface Props {
		classNames?: string;
		dropdownElement?: HTMLElement | undefined;
		forceAlignement?: Alignement | undefined;
		onClose: () => void;
		children?: import("svelte").Snippet;
	}

	let {
		classNames = "",
		dropdownElement = undefined,
		forceAlignement = undefined,
		onClose,
		children,
	}: Props = $props();

	// MUST start as left if forceAlignement is undefined, or the browser can't measure x and width
	let alignement: Alignement = $state(untrack(() => forceAlignement) ?? "left");
	let element: HTMLElement | undefined = $state();

	onMount(() => {
		document.addEventListener("click", handleClickDocument);

		if (!forceAlignement) {
			const docWidth = document.documentElement.clientWidth;
			const domRect = element?.getBoundingClientRect();
			alignement = (domRect?.left ?? 0) + (domRect?.width ?? 0) > docWidth ? "right" : "left";
		}
		element?.querySelector<HTMLElement>("a, button")?.focus();

		return () => document.removeEventListener("click", handleClickDocument);
	});

	function handleClickDocument(e: MouseEvent) {
		// Ignore clicks inside the dropdown itself (its button toggles the menu)
		const target = e.target as Node;
		if (target !== dropdownElement && !dropdownElement?.contains(target)) {
			onClose();
		}
	}
</script>

<div
	bind:this={element}
	class="dropdown-menu {alignement === 'right' ? 'align-right' : 'align-left'} {classNames}"
>
	<ul role="menu">
		{@render children?.()}
	</ul>
</div>
