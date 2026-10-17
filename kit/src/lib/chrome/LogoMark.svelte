<script lang="ts">
	// The supplied gradient disc, with its rectangular matte cropped away by a circular mask
	// (same crop as the Cerulean website's LogoMark). Never recolor or redraw it.
	import logo from "$lib/assets/logo.png";
</script>

<span class="logo-mark" aria-hidden="true">
	<img src={logo} alt="" width="256" height="250" />
</span>

<style>
	.logo-mark {
		position: relative;
		display: inline-block;
		flex: none;
		width: 26px;
		height: 26px;
		overflow: hidden;
		border-radius: 50%;
	}

	.logo-mark img {
		position: absolute;
		width: 121.95%;
		height: 119.05%;
		max-width: none;
		left: -10.975%;
		top: -9.525%;
	}
</style>
