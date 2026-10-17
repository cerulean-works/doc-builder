/**
 * Cerulean docs Worker: serves the static builds in R2 (contracts C1-C3 in
 * docs/source/architecture.md).
 *
 *   /                          landing page (server-rendered)
 *   /_projects.json            derived project manifest
 *   /robots.txt                disallow-all on preview
 *   /<p>, /<p>/                302 -> /<p>/<default>/guide/
 *   /<p>/_versions.json        derived version manifest
 *   /<p>/latest/<rest>         302 -> /<p>/<default>/<rest>
 *   /<p>/<section>/<rest>      302 -> /<p>/<default>/<section>/<rest>
 *   /<p>/<v>, /<p>/<v>/        302 -> /<p>/<v>/guide/
 *   /<p>/<v>/<rest>/           <p>/<v>/<rest>/index.html (or <rest>.md for Accept: text/markdown)
 *   /<p>/<v>/<rest>.<ext>      <p>/<v>/<rest>.<ext>
 *   /<p>/<v>/<rest>            308 -> /<p>/<v>/<rest>/
 */
import { type Env, isPreview } from "./env";
import { renderError, renderLanding } from "./html";
import {
	PROJECT_RE,
	VERSION_RE,
	getProjectsManifest,
	getVersionsManifest,
	manifestMaxAge,
} from "./manifests";
import { contentTypeFor, extensionOf } from "./mime";

const SECTIONS = new Set(["guide", "reference"]);
const SEGMENT_RE = /^[\p{L}\p{N}_~@+,=-][\p{L}\p{N}._~@+,=-]*$/u;
const MAX_SEGMENTS = 64;
const MAX_SEGMENT_LENGTH = 255;

const CACHE_IMMUTABLE = "public, max-age=31536000, immutable";
const CACHE_DOCUMENT = "public, max-age=60";
const CACHE_ASSET = "public, max-age=300";

interface Ctx {
	request: Request;
	url: URL;
	env: Env;
	ctx: ExecutionContext;
}

export default {
	async fetch(request, env, ctx): Promise<Response> {
		let response: Response;
		if (request.method !== "GET" && request.method !== "HEAD") {
			response = new Response("Method Not Allowed\n", {
				status: 405,
				headers: { allow: "GET, HEAD", "content-type": "text/plain; charset=utf-8" },
			});
		} else {
			response = await route({ request, url: new URL(request.url), env, ctx });
		}
		return finalize(request, env, response);
	},
} satisfies ExportedHandler<Env>;

function finalize(request: Request, env: Env, response: Response): Response {
	const out = new Response(request.method === "HEAD" ? null : response.body, response);
	out.headers.set("x-content-type-options", "nosniff");
	if (isPreview(env)) out.headers.set("x-robots-tag", "noindex");
	return out;
}

/** Splits and validates the path. `null` means traversal or an odd segment. */
function parsePath(pathname: string): { segments: string[]; trailingSlash: boolean } | null {
	const raw = pathname.slice(1);
	if (raw === "") return { segments: [], trailingSlash: true };
	const trailingSlash = raw.endsWith("/");
	const parts = (trailingSlash ? raw.slice(0, -1) : raw).split("/");
	if (parts.length > MAX_SEGMENTS) return null;
	const segments: string[] = [];
	for (const part of parts) {
		let seg: string;
		try {
			seg = decodeURIComponent(part);
		} catch {
			return null;
		}
		// Rejects "", ".", "..", dot-files, encoded slashes/backslashes and control characters.
		if (seg.length > MAX_SEGMENT_LENGTH || !SEGMENT_RE.test(seg)) return null;
		segments.push(seg);
	}
	return { segments, trailingSlash };
}

function joinPath(segments: string[], trailingSlash: boolean): string {
	return `/${segments.map(encodeURIComponent).join("/")}${trailingSlash && segments.length ? "/" : ""}`;
}

function redirect(c: Ctx, status: 302 | 308, path: string, cacheControl: string): Response {
	return new Response(null, {
		status,
		headers: { location: new URL(path + c.url.search, c.url).toString(), "cache-control": cacheControl },
	});
}

function htmlResponse(body: string, status: number, cacheControl = CACHE_DOCUMENT): Response {
	return new Response(body, {
		status,
		headers: { "content-type": "text/html; charset=utf-8", "cache-control": cacheControl },
	});
}

function jsonResponse(value: unknown, maxAge: number): Response {
	return new Response(JSON.stringify(value), {
		headers: {
			"content-type": "application/json; charset=utf-8",
			"cache-control": `public, max-age=${maxAge}`,
			"access-control-allow-origin": "*",
		},
	});
}

function globalError(c: Ctx, status: number): Response {
	const message = status === 404 ? "Page not found" : "Bad request";
	return htmlResponse(renderError(c.env.SITE_NAME, status, message, isPreview(c.env)), status);
}

async function defaultVersion(c: Ctx, project: string): Promise<string | null> {
	const manifest = await getVersionsManifest(c.env, c.ctx, c.url.origin, project);
	return manifest?.default ?? null;
}

async function route(c: Ctx): Promise<Response> {
	const parsed = parsePath(c.url.pathname);
	if (!parsed) return globalError(c, 400);
	const { segments, trailingSlash } = parsed;
	const [p, s1] = segments;

	if (p === undefined) {
		const projects = await getProjectsManifest(c.env, c.ctx, c.url.origin);
		return htmlResponse(renderLanding(c.env.SITE_NAME, projects, isPreview(c.env)), 200);
	}

	if (segments.length === 1 && !trailingSlash) {
		if (p === "_projects.json") {
			return jsonResponse(await getProjectsManifest(c.env, c.ctx, c.url.origin), manifestMaxAge(c.env));
		}
		if (p === "robots.txt") {
			const body = isPreview(c.env) ? "User-agent: *\nDisallow: /\n" : "User-agent: *\nAllow: /\n";
			return new Response(body, {
				headers: { "content-type": "text/plain; charset=utf-8", "cache-control": CACHE_ASSET },
			});
		}
	}

	if (!PROJECT_RE.test(p)) return globalError(c, 404);

	// /<p>, /<p>/
	if (s1 === undefined) {
		const def = await defaultVersion(c, p);
		if (!def) return globalError(c, 404);
		return redirect(c, 302, joinPath([p, def, "guide"], true), CACHE_DOCUMENT);
	}

	if (s1 === "_versions.json" && segments.length === 2 && !trailingSlash) {
		const manifest = await getVersionsManifest(c.env, c.ctx, c.url.origin, p);
		if (!manifest) return globalError(c, 404);
		return jsonResponse(manifest, manifestMaxAge(c.env));
	}

	// /<p>/latest/<rest> and version-less /<p>/<section>/<rest> (and /<p>/guide.md)
	const versionless = SECTIONS.has(s1) || SECTIONS.has(s1.replace(/\.md$/, ""));
	if (s1 === "latest" || versionless) {
		const def = await defaultVersion(c, p);
		if (!def) return globalError(c, 404);
		const rest = segments.slice(s1 === "latest" ? 2 : 1);
		const target = rest.length ? joinPath([p, def, ...rest], trailingSlash) : joinPath([p, def, "guide"], true);
		return redirect(c, 302, target, CACHE_DOCUMENT);
	}

	if (!VERSION_RE.test(s1)) return globalError(c, 404);

	// /<p>/<v>, /<p>/<v>/
	if (segments.length === 2) return redirect(c, 302, joinPath([p, s1, "guide"], true), CACHE_ASSET);

	return serveFromBuild(c, p, s1, segments.slice(2), trailingSlash);
}

function wantsMarkdown(accept: string | null): boolean {
	if (!accept) return false;
	let markdown = false;
	let html = false;
	for (const part of accept.toLowerCase().split(",")) {
		const [type, ...params] = part.split(";").map((s) => s.trim());
		const q = params.find((s) => s.startsWith("q="));
		if (q !== undefined && !(Number(q.slice(2)) > 0)) continue;
		if (type === "text/markdown" || type === "text/x-markdown") markdown = true;
		if (type === "text/html" || type === "application/xhtml+xml") html = true;
	}
	return markdown && !html;
}

function cacheControlFor(relKey: string): string {
	if (relKey.startsWith("_app/immutable/")) return CACHE_IMMUTABLE;
	const ext = extensionOf(relKey);
	if (ext === "html" || ext === "md" || relKey === "_app/version.json" || /^llms(-full)?\.txt$/.test(relKey)) {
		return CACHE_DOCUMENT;
	}
	return CACHE_ASSET;
}

function etagMatches(header: string, etag: string): boolean {
	if (header.trim() === "*") return true;
	const strip = (t: string) => t.trim().replace(/^W\//, "");
	return header.split(",").some((t) => strip(t) === strip(etag));
}

/** RFC 9110 evaluation for HEAD, which uses `head()` and so cannot rely on R2's `onlyIf`. */
function headPrecondition(request: Request, obj: R2Object): 304 | 412 | null {
	const ifMatch = request.headers.get("if-match");
	if (ifMatch !== null && !etagMatches(ifMatch, obj.httpEtag)) return 412;
	const ifNoneMatch = request.headers.get("if-none-match");
	if (ifNoneMatch !== null) return etagMatches(ifNoneMatch, obj.httpEtag) ? 304 : null;
	const ims = request.headers.get("if-modified-since");
	if (ims !== null) {
		const since = Date.parse(ims);
		if (!Number.isNaN(since) && Math.floor(obj.uploaded.getTime() / 1000) <= Math.floor(since / 1000)) return 304;
	}
	return null;
}

async function fetchObject(c: Ctx, key: string): Promise<{ obj: R2Object; body: ReadableStream | null; status: 200 | 304 | 412 } | null> {
	if (c.request.method === "HEAD") {
		const obj = await c.env.DOCS.head(key);
		if (!obj) return null;
		return { obj, body: null, status: headPrecondition(c.request, obj) ?? 200 };
	}
	const obj = await c.env.DOCS.get(key, { onlyIf: c.request.headers });
	if (!obj) return null;
	if ("body" in obj && obj.body) return { obj, body: obj.body, status: 200 };
	// Precondition failed: a strong-validator failure is 412, a cache hit is 304.
	const failedMatch = c.request.headers.has("if-match") || c.request.headers.has("if-unmodified-since");
	const noneMatch = c.request.headers.get("if-none-match");
	const status = failedMatch && !(noneMatch && etagMatches(noneMatch, obj.httpEtag)) ? 412 : 304;
	return { obj, body: null, status };
}

async function serveFromBuild(c: Ctx, project: string, version: string, rest: string[], trailingSlash: boolean): Promise<Response> {
	const base = `${project}/${version}/`;
	const relPath = rest.join("/");
	const last = rest[rest.length - 1]!;

	let relKey: string;
	let isPage = false;
	if (trailingSlash) {
		relKey = `${relPath}/index.html`;
		isPage = true;
	} else if (last === "index.html") {
		// Page URLs never contain .html (C1).
		return redirect(c, 308, joinPath([project, version, ...rest.slice(0, -1)], true), CACHE_ASSET);
	} else if (extensionOf(last)) {
		relKey = relPath;
	} else {
		return redirect(c, 308, joinPath([project, version, ...rest], true), CACHE_ASSET);
	}

	let found = null as Awaited<ReturnType<typeof fetchObject>>;
	if (isPage && wantsMarkdown(c.request.headers.get("accept"))) {
		const mdKey = `${relPath}.md`;
		found = await fetchObject(c, base + mdKey);
		if (found) relKey = mdKey;
	}
	found ??= await fetchObject(c, base + relKey);

	if (!found) {
		// `/<p>/<v>/api/v1.2` may be a page whose last segment merely looks like a file.
		if (!isPage && (await c.env.DOCS.head(`${base}${relPath}/index.html`))) {
			return redirect(c, 308, joinPath([project, version, ...rest], true), CACHE_ASSET);
		}
		return versionNotFound(c, base);
	}

	const { obj, body, status } = found;
	const headers = new Headers({
		etag: obj.httpEtag,
		"last-modified": obj.uploaded.toUTCString(),
		"cache-control": cacheControlFor(relKey),
	});
	if (isPage) headers.set("vary", "Accept");
	if (status === 412) return new Response(null, { status, headers });
	headers.set("content-type", contentTypeFor(relKey, obj.httpMetadata?.contentType));
	if (status === 304) return new Response(null, { status, headers });
	if (c.request.method === "HEAD") headers.set("content-length", String(obj.size));
	return new Response(body, { status, headers });
}

/** A missing page under an existing build gets that build's own 404.html (C3). */
async function versionNotFound(c: Ctx, base: string): Promise<Response> {
	const page = await c.env.DOCS.get(`${base}404.html`);
	if (!page) return globalError(c, 404);
	return new Response(page.body, {
		status: 404,
		headers: { "content-type": "text/html; charset=utf-8", "cache-control": CACHE_DOCUMENT },
	});
}
