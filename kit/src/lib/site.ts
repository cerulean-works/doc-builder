import siteJson from "$lib/generated/site.json";
import type { Section, SiteData, TocEntry } from "./types";

export const site = siteJson as SiteData;

export const SECTIONS: { id: Section; label: string }[] = [
	{ id: "guide", label: "Guide" },
	{ id: "reference", label: "Reference" },
];

/** Sections that actually have pages in this build. */
export const availableSections = SECTIONS.filter(({ id }) => (site.toctree[id] ?? []).length > 0);

/** `pr_12` → "Preview · PR #12"; other versions are shown as-is. */
export function versionLabel(version: string): string {
	const pr = /^pr_(\d+)$/.exec(version);
	return pr ? `Preview · PR #${pr[1]}` : version;
}

/** Normalises a pathname so `/a/b` and `/a/b/` compare equal. */
export function withTrailingSlash(pathname: string): string {
	return pathname.endsWith("/") ? pathname : `${pathname}/`;
}

/**
 * Splits a pathname under the base path into its section and the rest of the page path,
 * e.g. `/p/v/guide/quickstart/` → `{ section: "guide", rest: "quickstart/" }`.
 */
export function splitPath(pathname: string, base: string): { section?: Section; rest: string } {
	const relative = pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
	const match = /^\/(guide|reference)(?:\/(.*))?$/.exec(relative);
	if (!match) return { rest: relative.replace(/^\//, "") };
	return { section: match[1] as Section, rest: match[2] ?? "" };
}

/** Depth-first list of the entries that are pages, in toctree order. */
export function flattenToc(entries: TocEntry[] = []): TocEntry[] {
	return entries.flatMap((entry) => [
		...(entry.url ? [entry] : []),
		...flattenToc(entry.sections ?? []),
	]);
}

/** Whether `entry` or one of its descendants is the page at `pathname`. */
export function containsPath(entry: TocEntry, pathname: string): boolean {
	if (entry.url && withTrailingSlash(entry.url) === withTrailingSlash(pathname)) return true;
	return (entry.sections ?? []).some((child) => containsPath(child, pathname));
}
