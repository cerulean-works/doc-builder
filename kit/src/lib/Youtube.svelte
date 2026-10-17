<script lang="ts">
	interface Props {
		id: string;
	}

	let { id }: Props = $props();
</script>

<div class="video-embed">
	<iframe
		src="https://www.youtube-nocookie.com/embed/{id}"
		title="YouTube video player"
		loading="lazy"
		allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
		allowfullscreen
	></iframe>
</div>
