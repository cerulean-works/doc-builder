<script lang="ts">
	import { onMount, tick } from "svelte";
	import { tooltip } from "./tooltipAction.svelte";
	import IconCopyLink from "./IconCopyLink.svelte";
	import { escapeHtml } from "./utils";

	type Parameter = {
		anchor: string;
		name: string;
		description: string;
	};

	interface Props {
		anchor: string;
		name: string;
		parameters?: { name: string; val: string }[];
		parametersDescription?: Parameter[];
		parameterGroups?: {
			title: string;
			parametersDescription: Parameter[];
		}[];
		returnDescription?: string;
		returnType?: string;
		isYield?: boolean;
		raiseDescription?: string;
		raiseType?: string;
		source?: string | undefined;
		hashlink?: string | undefined;
		isGetSetDescriptor?: boolean;
	}

	let {
		anchor,
		name,
		parameters = [],
		parametersDescription,
		parameterGroups,
		returnDescription,
		returnType,
		isYield = false,
		raiseDescription,
		raiseType,
		source = undefined,
		hashlink = $bindable(),
		isGetSetDescriptor = false,
	}: Props = $props();

	let parametersElement = $state<HTMLElement>();
	let collapsed: boolean = $state(false);

	let tooltipMapper: Record<string, string> = $derived(
		Object.fromEntries(
			(parametersDescription ?? []).map(({ name: paramName, description }) => [
				paramName,
				description,
			])
		)
	);
	let returnsTitle = $derived(isYield ? "Yields" : "Returns");
	let returnsAnchor = $derived(returnsTitle.toLowerCase());

	/** Activates a clickable parameter / return type with Enter or Space, like a button. */
	function onKeyActivate(event: KeyboardEvent, target: string, isAnchorExists: boolean) {
		if (event.key === "Enter" || event.key === " ") {
			event.preventDefault();
			onClick(target, isAnchorExists);
		}
	}

	onMount(() => {
		hashlink = window.location.hash.substring(1);
		const hashlinksEls =
			parametersElement?.querySelectorAll<HTMLAnchorElement>('[href^="#"]') ?? [];
		const hashlinks = [...hashlinksEls].map((el) => el.id);
		const containsAnchor = !!hashlink && hashlinks.includes(hashlink);
		collapsed = !containsAnchor && (parametersElement?.clientHeight ?? 0) > 500;
		onHashChange();
	});

	async function onClick(target: string, isAnchorExists: boolean) {
		if (isAnchorExists) {
			collapsed = false;
			await tick();
			window.location.hash = target;
		}
	}

	/** Splits `pkg.mod.Name` into a muted `pkg.mod.` prefix and the object name. */
	function splitName(fullName: string) {
		const path = fullName.split(".");
		const last = path.pop() ?? "";
		return { prefix: path.length ? `${path.join(".")}.` : "", last };
	}

	function signature(fullName: string) {
		if (fullName.startsWith("class ")) {
			const { prefix, last } = splitName(fullName.substring("class ".length));
			return `<span class="docstring-kind">class</span> <span class="docstring-prefix">${escapeHtml(prefix)}</span><span class="docstring-name">${escapeHtml(last)}</span>`;
		}
		const { prefix, last } = splitName(fullName);
		const kind = isGetSetDescriptor ? `<span class="docstring-kind">property</span> ` : "";
		return `${kind}<span class="docstring-prefix">${escapeHtml(prefix)}</span><span class="docstring-name">${escapeHtml(last)}</span>`;
	}

	function replaceParagraphWithSpan(txt: string): string {
		const REGEX_P = /\s*<p>(((?!<p>).)*)<\/p>\s*/gms;
		return txt.replace(REGEX_P, (_, content) => `<span>${content}</span>`);
	}

	function onHashChange() {
		hashlink = window.location.hash.substring(1);
	}
</script>

<svelte:window onhashchange={onHashChange} />

<div class="docstring-body" class:is-target={hashlink === anchor}>
	<div class="docstring-header">
		<!-- The anchor sits on the signature; Python's heading (if any) carries its own id. -->
		<code class="docstring-signature" id={anchor}>{@html signature(name)}</code>
		<a class="header-link" href="#{anchor}" aria-label="Link to {name}" data-pagefind-ignore
			><IconCopyLink /></a
		>
		{#if source}
			<a class="docstring-source" href={source} target="_blank" rel="noopener" data-pagefind-ignore
				>source</a
			>
		{/if}
	</div>
	{#if !isGetSetDescriptor}
		<p class="docstring-params">
			<span>(</span>
			{#each parameters as { name: paramName, val }}
				<span
					use:tooltip={tooltipMapper[paramName] || ""}
					class="comma"
					class:has-description={!!tooltipMapper[paramName]}
					role="button"
					tabindex={tooltipMapper[paramName] ? 0 : -1}
					onkeydown={(event) =>
						onKeyActivate(event, `${anchor}.${paramName}`, !!tooltipMapper[paramName])}
					onclick={(event: MouseEvent) => {
						event.preventDefault();
						event.stopPropagation();
						onClick(`${anchor}.${paramName}`, !!tooltipMapper[paramName]);
					}}
				>
					<span class="docstring-param"
						>{paramName}<span class="docstring-param-val">{val}</span></span
					>
				</span>
			{/each}
			<span>)</span>
			{#if returnType}
				<span class="docstring-arrow">→</span>
				<span
					use:tooltip={returnDescription || ""}
					class="docstring-return-type"
					class:has-description={!!returnDescription}
					role="button"
					tabindex={returnDescription ? 0 : -1}
					onkeydown={(event) =>
						onKeyActivate(event, `${anchor}.${returnsAnchor}`, !!returnDescription)}
					onclick={(event: MouseEvent) => {
						event.preventDefault();
						event.stopPropagation();
						onClick(`${anchor}.${returnsAnchor}`, !!returnDescription);
					}}>{@html replaceParagraphWithSpan(returnType)}</span
				>
			{/if}
		</p>
	{/if}

	<!-- `docstring-details` is kept as a stable hook for crawlers -->
	<div class="docstring-details" class:collapsed bind:this={parametersElement}>
		{#if parametersDescription?.length}
			<p class="docstring-section-title">Parameters</p>
			<ul class="docstring-param-list">
				{#each parametersDescription as { anchor: paramAnchor, description }}
					<li class:is-target={hashlink === paramAnchor}>
						<a
							id={paramAnchor}
							class="header-link"
							href={`#${paramAnchor}`}
							aria-label="Link to this parameter"
							data-pagefind-ignore><IconCopyLink /></a
						>
						<span>{@html description}</span>
					</li>
				{/each}
			</ul>
		{/if}
		{#if parameterGroups}
			{#each parameterGroups as { title, parametersDescription: groupParams }}
				<p class="docstring-section-title">{@html escapeHtml(title)}</p>
				<ul class="docstring-param-list">
					{#each groupParams as { anchor: paramAnchor, description }}
						<li class:is-target={hashlink === paramAnchor}>
							<a
								id={paramAnchor}
								class="header-link"
								href={`#${paramAnchor}`}
								aria-label="Link to this parameter"
								data-pagefind-ignore><IconCopyLink /></a
							>
							<span>{@html description}</span>
						</li>
					{/each}
				</ul>
			{/each}
		{/if}
		{#if returnType}
			<div
				id={`${anchor}.${returnsAnchor}`}
				class="docstring-section-title docstring-returns"
				class:is-target={hashlink === `${anchor}.${returnsAnchor}`}
			>
				<span>{@html escapeHtml(returnsTitle)}</span>
				<span class="docstring-type">{@html returnType}</span>
			</div>
			<!-- a <div>, not a <p>: the description contains its own <p> elements -->
			<div class="docstring-description">{@html returnDescription || ""}</div>
		{/if}
		{#if raiseType}
			<div class="docstring-section-title docstring-returns" id={`${anchor}.raises`}>
				<span>Raises</span>
				<span class="docstring-type">{@html raiseType}</span>
			</div>
			<div class="docstring-description">{@html raiseDescription || ""}</div>
		{/if}
	</div>
	{#if collapsed}
		<button
			type="button"
			class="outline-button docstring-expand"
			onclick={() => (collapsed = false)}
		>
			Show all {parametersDescription?.length ?? ""} parameters
		</button>
	{/if}
</div>
