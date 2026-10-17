<script lang="ts">
	import CopyButton from "./CopyButton.svelte";

	interface Props {
		code?: string;
		highlighted?: string;
		lang?: string;
		wrap?: boolean;
		classNames?: string;
	}

	let { code = "", highlighted = "", lang = "", wrap = false, classNames = "" }: Props = $props();
</script>

<div class="code-block {classNames}">
	<div class="code-block-copy">
		<CopyButton label="Copy code" value={code} />
	</div>
	<pre class="hljs {lang ? `language-${lang}` : ''} {wrap ? 'wrap' : ''}"><code
			>{@html highlighted}</code
		></pre>
</div>
