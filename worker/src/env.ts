export interface Env {
	/** Bucket holding `<project>/<version>/...` builds, markers and `_project.json` (C2). */
	DOCS: R2Bucket;
	/** "true" on the PR-preview deployment: adds noindex everywhere. */
	PREVIEW: string;
	/** Shown on the landing page and the built-in 404 page. */
	SITE_NAME: string;
	/**
	 * Seconds to cache the derived manifests in the Cache API (clamped to 0..60).
	 * Optional; defaults to 60. `pnpm run dev` sets it to 0 so freshly seeded
	 * versions show up immediately.
	 */
	MANIFEST_CACHE_SECONDS?: string;
}

export const isPreview = (env: Env): boolean => env.PREVIEW === "true";
