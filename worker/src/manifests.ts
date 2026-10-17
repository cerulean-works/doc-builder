/**
 * Manifests derived from R2 listings (C2). Nothing here reads a stored
 * manifest, so concurrent publishes never race on a shared file:
 *
 * - versions come from the `<p>/_versions/<v>` marker objects (written last by
 *   publish), so a half-uploaded version is invisible;
 * - projects come from the top-level `<p>/` prefixes plus `<p>/_project.json`.
 */
import { type Env, isPreview } from "./env";
import { type VersionEntry, type VersionsManifest, compareVersions, pickDefault } from "./versions";

export interface ProjectEntry {
	name: string;
	title: string;
	description: string;
	repo: string | null;
	default: string;
}

export const PROJECT_RE = /^[A-Za-z0-9][\w-]*$/;
export const VERSION_RE = /^[A-Za-z0-9][\w.+-]*$/;
const REPO_RE = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const MAX_PROJECT_JSON_BYTES = 64 * 1024;

/** Paginates over every marker under `<p>/_versions/`. */
export async function listVersions(bucket: R2Bucket, project: string): Promise<VersionEntry[]> {
	const prefix = `${project}/_versions/`;
	const entries: VersionEntry[] = [];
	let cursor: string | undefined;
	do {
		const page = await bucket.list({ prefix, cursor, include: ["customMetadata"] });
		for (const obj of page.objects) {
			const version = obj.key.slice(prefix.length);
			if (!VERSION_RE.test(version) || version === "latest") continue;
			const meta = obj.customMetadata ?? {};
			entries.push({ version, commit: meta.commit ?? null, built_at: meta.built_at ?? null });
		}
		// R2 may return fewer than `limit` objects while still truncated (for
		// example when metadata is included), so only `truncated` ends the loop.
		cursor = page.truncated ? page.cursor : undefined;
	} while (cursor);
	return entries.sort((a, b) => compareVersions(a.version, b.version));
}

/** Paginates over the top-level `<p>/` prefixes. */
export async function listProjectNames(bucket: R2Bucket): Promise<string[]> {
	const names = new Set<string>();
	let cursor: string | undefined;
	do {
		const page = await bucket.list({ delimiter: "/", cursor });
		for (const prefix of page.delimitedPrefixes) {
			const name = prefix.slice(0, -1);
			if (PROJECT_RE.test(name)) names.add(name);
		}
		cursor = page.truncated ? page.cursor : undefined;
	} while (cursor);
	return [...names].sort();
}

export async function buildVersionsManifest(bucket: R2Bucket, project: string): Promise<VersionsManifest | null> {
	const versions = await listVersions(bucket, project);
	const def = pickDefault(versions.map((v) => v.version));
	if (def === null) return null;
	return { default: def, versions };
}

function str(value: unknown, max: number): string | null {
	return typeof value === "string" && value.trim() !== "" ? value.trim().slice(0, max) : null;
}

async function readProjectJson(bucket: R2Bucket, project: string): Promise<Record<string, unknown>> {
	const obj = await bucket.get(`${project}/_project.json`);
	if (!obj || obj.size > MAX_PROJECT_JSON_BYTES) return {};
	try {
		const parsed: unknown = JSON.parse(await obj.text());
		return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
	} catch {
		return {};
	}
}

export async function buildProjectsManifest(env: Env): Promise<ProjectEntry[]> {
	const names = await listProjectNames(env.DOCS);
	const preview = isPreview(env);
	const entries = await Promise.all(
		names.map(async (name): Promise<ProjectEntry | null> => {
			const [manifest, meta] = await Promise.all([
				buildVersionsManifest(env.DOCS, name),
				// `_project.json` is only ever published to prod (C2).
				preview ? Promise.resolve<Record<string, unknown>>({}) : readProjectJson(env.DOCS, name),
			]);
			if (!manifest) return null; // no markers: invisible
			const repo = str(meta.repo, 200);
			return {
				name,
				title: str(meta.title, 200) ?? name,
				description: str(meta.description, 1000) ?? "",
				repo: repo && REPO_RE.test(repo) ? repo : null,
				default: manifest.default,
			};
		}),
	);
	return entries.filter((e): e is ProjectEntry => e !== null);
}

function cacheSeconds(env: Env): number {
	const raw = env.MANIFEST_CACHE_SECONDS;
	const n = raw === undefined || raw === "" ? 60 : Number(raw);
	return Number.isFinite(n) ? Math.max(0, Math.min(60, Math.floor(n))) : 60;
}

/**
 * Memoises `compute` in the Cache API for at most 60 seconds. `origin` keeps
 * prod and preview apart; the `/__manifests/` path is never routed publicly.
 */
async function cached<T>(env: Env, ctx: ExecutionContext, origin: string, name: string, compute: () => Promise<T>): Promise<T> {
	const ttl = cacheSeconds(env);
	if (ttl === 0) return compute();
	const cache = caches.default;
	const key = new Request(`${origin}/__manifests/v1/${name}`);
	const hit = await cache.match(key);
	if (hit) return (await hit.json()) as T;
	const value = await compute();
	ctx.waitUntil(
		cache.put(
			key,
			new Response(JSON.stringify(value), {
				headers: { "content-type": "application/json", "cache-control": `public, max-age=${ttl}` },
			}),
		),
	);
	return value;
}

export function getVersionsManifest(env: Env, ctx: ExecutionContext, origin: string, project: string) {
	return cached(env, ctx, origin, `versions/${project}`, () => buildVersionsManifest(env.DOCS, project));
}

export function getProjectsManifest(env: Env, ctx: ExecutionContext, origin: string) {
	return cached(env, ctx, origin, "projects", () => buildProjectsManifest(env));
}

export function manifestMaxAge(env: Env): number {
	return cacheSeconds(env);
}
