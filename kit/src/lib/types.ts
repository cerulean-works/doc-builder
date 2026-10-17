/** A node of a page's heading tree, exported by every page as `metadata` (docs/source/architecture.md, C5). */
export interface HeadingNode {
	title: string;
	local: string;
	depth: number;
	sections?: HeadingNode[];
}

export type Section = "guide" | "reference";

/** A toctree entry from `site.json` (C4/C5). Entries with a `local` also carry their resolved `url`. */
export interface TocEntry {
	title: string;
	local?: string;
	url?: string;
	sections?: TocEntry[];
	isExpanded?: boolean;
}

/** `src/lib/generated/site.json`, staged by doc-builder (C5). */
export interface SiteData {
	project: string;
	title: string;
	description?: string;
	version: string;
	repo?: string;
	sourceRef?: string;
	toctree: Partial<Record<Section, TocEntry[]>>;
}

/** `GET /<project>/_versions.json`, served by the Worker (C2). */
export interface VersionsManifest {
	default: string;
	versions: { version: string; commit?: string; built_at?: string }[];
}

/** `GET /_projects.json`, served by the Worker (C2). */
export type ProjectsManifest = {
	name: string;
	title?: string;
	description?: string;
	repo?: string;
	default?: string;
}[];
