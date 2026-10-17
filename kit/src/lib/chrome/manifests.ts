import type { ProjectsManifest, VersionsManifest } from "../types";

/**
 * The Worker derives these manifests from R2 (docs/source/architecture.md, C2). They live at the origin
 * root, outside this build's base path, and don't exist in local dev: callers treat `null` as
 * "hide the switcher".
 */
const cache = new Map<string, Promise<unknown>>();

function fetchJson<T>(url: string, isValid: (value: unknown) => boolean): Promise<T | null> {
	if (!cache.has(url)) {
		cache.set(
			url,
			fetch(url, { headers: { Accept: "application/json" } })
				.then((response) => (response.ok ? response.json() : null))
				.then((value) => (isValid(value) ? value : null))
				.catch(() => null)
		);
	}
	return cache.get(url) as Promise<T | null>;
}

export function fetchVersions(project: string): Promise<VersionsManifest | null> {
	return fetchJson<VersionsManifest>(`/${encodeURIComponent(project)}/_versions.json`, (value) =>
		Array.isArray((value as VersionsManifest | null)?.versions)
	);
}

export function fetchProjects(): Promise<ProjectsManifest | null> {
	return fetchJson<ProjectsManifest>("/_projects.json", (value) => Array.isArray(value));
}
