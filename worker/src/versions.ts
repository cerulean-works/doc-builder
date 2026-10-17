/**
 * Version ordering and default-version selection (C1, C2).
 *
 * Versions are `main`, git tags (`v1.2.0`, `1.2.0`, `v2.0.0rc1`, ...) or
 * `pr_<N>`. Tags are compared as semver, with PEP 440 style suffixes
 * (`a1`, `b2`, `rc1`, `.dev0`) treated as prereleases so Python projects sort
 * sensibly too.
 */

export interface VersionEntry {
	version: string;
	commit: string | null;
	built_at: string | null;
}

export interface VersionsManifest {
	default: string;
	versions: VersionEntry[];
}

interface ParsedTag {
	core: number[];
	/** Empty for a stable release. */
	pre: string;
	post: boolean;
}

const TAG_RE = /^v?(\d+(?:\.\d+)*)(.*)$/i;
const PR_RE = /^pr_(\d+)$/;

export function parseTag(tag: string): ParsedTag | null {
	const m = TAG_RE.exec(tag);
	if (!m) return null;
	const core = m[1]!.split(".").map(Number);
	if (core.some((n) => !Number.isSafeInteger(n))) return null;
	// Build metadata never affects precedence.
	let rest = m[2]!.replace(/\+[0-9a-z.-]*$/i, "");
	if (/^[-.]?post\d*$/i.test(rest)) return { core, pre: "", post: true };
	rest = rest.replace(/^[-.]/, "");
	if (rest !== "" && !/^[0-9a-z.-]+$/i.test(rest)) return null;
	return { core, pre: rest, post: false };
}

export function isStableTag(tag: string): boolean {
	const parsed = parseTag(tag);
	return parsed !== null && parsed.pre === "";
}

function comparePre(a: string, b: string): number {
	const as = a.split(/[.-]|(?<=\d)(?=\D)|(?<=\D)(?=\d)/);
	const bs = b.split(/[.-]|(?<=\d)(?=\D)|(?<=\D)(?=\d)/);
	for (let i = 0; i < Math.max(as.length, bs.length); i++) {
		const x = as[i];
		const y = bs[i];
		if (x === undefined) return -1;
		if (y === undefined) return 1;
		const xn = /^\d+$/.test(x);
		const yn = /^\d+$/.test(y);
		if (xn && yn) {
			const d = Number(x) - Number(y);
			if (d !== 0) return d;
		} else if (xn !== yn) {
			return xn ? -1 : 1;
		} else if (x !== y) {
			return x < y ? -1 : 1;
		}
	}
	return 0;
}

/** Ascending semver comparison of two parsed tags. */
export function compareTags(a: ParsedTag, b: ParsedTag): number {
	for (let i = 0; i < Math.max(a.core.length, b.core.length); i++) {
		const d = (a.core[i] ?? 0) - (b.core[i] ?? 0);
		if (d !== 0) return d;
	}
	if (a.pre === "" && b.pre !== "") return 1;
	if (a.pre !== "" && b.pre === "") return -1;
	if (a.pre !== "" && b.pre !== "") return comparePre(a.pre, b.pre);
	return Number(a.post) - Number(b.post);
}

function rank(version: string): number {
	if (version === "main") return 0;
	if (parseTag(version)) return 1;
	if (PR_RE.test(version)) return 3;
	return 2; // any other tag name
}

/** `main` first, then tags in descending semver order, then other names, then PRs (newest first). */
export function compareVersions(a: string, b: string): number {
	const ra = rank(a);
	const rb = rank(b);
	if (ra !== rb) return ra - rb;
	if (ra === 1) return compareTags(parseTag(b)!, parseTag(a)!);
	if (ra === 3) return Number(PR_RE.exec(b)![1]) - Number(PR_RE.exec(a)![1]);
	return a < b ? 1 : a > b ? -1 : 0;
}

/**
 * The highest non-prerelease semver tag, else `main`.
 *
 * Contract C1 says "`main` if there are no tags". On the preview bucket there
 * is usually no `main` at all, so when `main` is absent too we fall back to the
 * first version in manifest order (the newest PR) rather than pointing at a
 * version that 404s.
 */
export function pickDefault(versions: string[]): string | null {
	let best: { tag: string; parsed: ParsedTag } | null = null;
	for (const v of versions) {
		const parsed = parseTag(v);
		if (!parsed || parsed.pre !== "") continue;
		if (!best || compareTags(parsed, best.parsed) > 0) best = { tag: v, parsed };
	}
	if (best) return best.tag;
	if (versions.includes("main")) return "main";
	return [...versions].sort(compareVersions)[0] ?? null;
}
