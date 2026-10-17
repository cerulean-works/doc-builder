import { createExecutionContext, waitOnExecutionContext } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { beforeAll, describe, expect, it } from "vitest";
import worker from "../src/index";
import type { Env } from "../src/env";
import { EVIL_PROJECT_JSON, HASH, SAMPLE_KEYS, SAMPLE_PROJECT_JSON, seed } from "./fixtures";

const ORIGIN = "https://docs.test";

async function call(path: string, init: RequestInit = {}, overrides: Partial<Env> & { origin?: string } = {}) {
	const { origin = ORIGIN, ...vars } = overrides;
	const request = new Request<unknown, IncomingRequestCfProperties>(new URL(path, origin), { redirect: "manual", ...init } as RequestInit<IncomingRequestCfProperties>);
	const ctx = createExecutionContext();
	const response = await worker.fetch(request, { ...env, ...vars }, ctx);
	await waitOnExecutionContext(ctx);
	return response;
}

const preview = (path: string, init: RequestInit = {}) =>
	call(path, init, { PREVIEW: "true", SITE_NAME: "Cerulean Docs Preview", origin: "https://preview.test" });

function location(res: Response): string | null {
	const loc = res.headers.get("location");
	return loc === null ? null : loc.startsWith(ORIGIN) ? loc.slice(ORIGIN.length) : loc;
}

beforeAll(async () => {
	await seed(env.DOCS);
});

describe("fixture", () => {
	it("seeds every key from docs/fixtures/r2-keys.txt", async () => {
		expect(SAMPLE_KEYS.length).toBeGreaterThan(15);
		for (const key of SAMPLE_KEYS) expect(await env.DOCS.head(key), key).not.toBeNull();
	});
});

describe("redirects (C1)", () => {
	it.each([
		["/sample", "/sample/v0.1.0/guide/"],
		["/sample/", "/sample/v0.1.0/guide/"],
		["/sample/main", "/sample/main/guide/"],
		["/sample/main/", "/sample/main/guide/"],
		["/sample/v0.1.0/", "/sample/v0.1.0/guide/"],
		["/sample/guide/quickstart/", "/sample/v0.1.0/guide/quickstart/"],
		["/sample/guide/", "/sample/v0.1.0/guide/"],
		["/sample/reference/api/utils/", "/sample/v0.1.0/reference/api/utils/"],
		["/sample/guide.md", "/sample/v0.1.0/guide.md"],
		["/sample/latest", "/sample/v0.1.0/guide/"],
		["/sample/latest/", "/sample/v0.1.0/guide/"],
		["/sample/latest/guide/quickstart/", "/sample/v0.1.0/guide/quickstart/"],
		["/sample/latest/reference/api/utils.md", "/sample/v0.1.0/reference/api/utils.md"],
		["/sample/latest/guide/quickstart/?q=install", "/sample/v0.1.0/guide/quickstart/?q=install"],
	])("%s -> %s (302)", async (from, to) => {
		const res = await call(from);
		expect(res.status).toBe(302);
		expect(location(res)).toBe(to);
	});

	it("never serves latest in place", async () => {
		const res = await call("/sample/latest/guide/");
		expect(res.status).toBe(302);
		expect(await res.text()).toBe("");
	});

	it("adds the trailing slash with a 308", async () => {
		for (const [from, to] of [
			["/sample/v0.1.0/guide/quickstart", "/sample/v0.1.0/guide/quickstart/"],
			["/sample/v0.1.0/guide", "/sample/v0.1.0/guide/"],
			["/sample/v0.1.0/guide/quickstart?x=1", "/sample/v0.1.0/guide/quickstart/?x=1"],
			["/sample/v0.1.0/guide/index.html", "/sample/v0.1.0/guide/"],
		]) {
			const res = await call(from!);
			expect(res.status, from).toBe(308);
			expect(location(res), from).toBe(to);
		}
	});

	it("404s for unknown projects instead of redirecting", async () => {
		expect((await call("/nope/")).status).toBe(404);
		expect((await call("/nope/latest/guide/")).status).toBe(404);
		expect((await call("/hidden/")).status).toBe(404);
	});
});

describe("default version", () => {
	it("is the highest stable semver tag", async () => {
		expect(location(await call("/multi/"))).toBe("/multi/v1.10.0/guide/");
	});

	it("skips prereleases", async () => {
		expect(location(await call("/sample/"))).toBe("/sample/v0.1.0/guide/");
		expect(location(await call("/prerel/"))).toBe("/prerel/main/guide/");
	});

	it("is main when there are no tags", async () => {
		expect(location(await call("/onlymain/"))).toBe("/onlymain/main/guide/");
		expect(location(await call("/onlymain/latest/reference/"))).toBe("/onlymain/main/reference/");
	});
});

describe("key mapping", () => {
	it.each([
		["/sample/v0.1.0/guide/", "sample/v0.1.0/guide/index.html", "text/html; charset=utf-8"],
		["/sample/v0.1.0/guide/quickstart/", "sample/v0.1.0/guide/quickstart/index.html", "text/html; charset=utf-8"],
		["/sample/v0.1.0/reference/api/utils/", "sample/v0.1.0/reference/api/utils/index.html", "text/html; charset=utf-8"],
		["/sample/v0.1.0/guide/quickstart.md", "sample/v0.1.0/guide/quickstart.md", "text/markdown; charset=utf-8"],
		["/sample/v0.1.0/guide.md", "sample/v0.1.0/guide.md", "text/markdown; charset=utf-8"],
		["/sample/v0.1.0/llms.txt", "sample/v0.1.0/llms.txt", "text/plain; charset=utf-8"],
		["/sample/v0.1.0/imgs/pixel.png", "sample/v0.1.0/imgs/pixel.png", "image/png"],
		["/sample/v0.1.0/pagefind/pagefind.js", "sample/v0.1.0/pagefind/pagefind.js", "text/javascript; charset=utf-8"],
		["/sample/main/guide/quickstart/", "sample/main/guide/quickstart/index.html", "text/html; charset=utf-8"],
	])("%s serves %s", async (path, key, type) => {
		const res = await call(path);
		expect(res.status).toBe(200);
		expect(res.headers.get("content-type")).toBe(type);
		expect(new TextDecoder().decode(await res.arrayBuffer())).toContain(key);
	});

	it("rejects traversal and odd segments", async () => {
		// The URL parser already resolves `..` and `%2e%2e`; nothing may escape the build.
		for (const path of ["/sample/v0.1.0/%2e%2e/%2e%2e/evil/_project.json", "/sample/v0.1.0/../../evil/_project.json"]) {
			const res = await call(path);
			expect(res.status, path).toBe(404);
			expect(await res.text()).not.toContain("alert");
		}
		for (const path of [
			"/sample/v0.1.0/%2e%2e%2f%2e%2e%2fevil/_project.json",
			"/sample/v0.1.0/..%5C..%5Cevil/_project.json",
			"/sample/v0.1.0/a%2Fb/",
			"/sample/v0.1.0/a%5Cb/",
			"/sample//guide/",
			"/sample/v0.1.0/.env",
			"/sample/v0.1.0/%00/",
			"/sample/v0.1.0/%E0%A4%A/",
		]) {
			expect((await call(path)).status, path).toBe(400);
		}
	});

	it("does not expose markers or reserved names", async () => {
		expect((await call("/sample/_versions/v0.1.0")).status).toBe(404);
		expect((await call("/sample/_project.json")).status).toBe(404);
		expect((await call("/_app/")).status).toBe(404);
	});

	it("serves GET and HEAD only", async () => {
		const post = await call("/sample/v0.1.0/guide/", { method: "POST" });
		expect(post.status).toBe(405);
		expect(post.headers.get("allow")).toBe("GET, HEAD");
		const head = await call("/sample/v0.1.0/guide/", { method: "HEAD" });
		expect(head.status).toBe(200);
		expect(head.headers.get("content-type")).toBe("text/html; charset=utf-8");
		expect(head.headers.get("etag")).toBeTruthy();
		expect(await head.text()).toBe("");
	});
});

describe("cache headers", () => {
	it("marks _app/immutable as immutable", async () => {
		for (const rel of [`_app/immutable/entry/start.${HASH}.js`, `_app/immutable/assets/0.${HASH}.css`]) {
			const res = await call(`/sample/v0.1.0/${rel}`);
			expect(res.status, rel).toBe(200);
			expect(res.headers.get("cache-control")).toBe("public, max-age=31536000, immutable");
		}
		const css = await call(`/sample/v0.1.0/_app/immutable/assets/0.${HASH}.css`);
		expect(css.headers.get("content-type")).toBe("text/css; charset=utf-8");
	});

	it("gives HTML a short cache and other assets about five minutes", async () => {
		expect((await call("/sample/v0.1.0/guide/")).headers.get("cache-control")).toBe("public, max-age=60");
		expect((await call("/sample/v0.1.0/imgs/pixel.png")).headers.get("cache-control")).toBe("public, max-age=300");
		expect((await call("/sample/v0.1.0/favicon.png")).headers.get("cache-control")).toBe("public, max-age=300");
	});
});

describe("conditional requests", () => {
	it("returns 304 for a matching If-None-Match on GET and HEAD", async () => {
		const first = await call("/sample/v0.1.0/guide/quickstart/");
		const etag = first.headers.get("etag")!;
		expect(etag).toMatch(/^"[^"]+"$/);
		await first.arrayBuffer();

		for (const method of ["GET", "HEAD"]) {
			const res = await call("/sample/v0.1.0/guide/quickstart/", { method, headers: { "if-none-match": etag } });
			expect(res.status, method).toBe(304);
			expect(res.headers.get("etag")).toBe(etag);
			expect(await res.text()).toBe("");
		}
	});

	it("returns 200 for a stale ETag", async () => {
		const res = await call("/sample/v0.1.0/guide/quickstart/", { headers: { "if-none-match": '"stale"' } });
		expect(res.status).toBe(200);
		await res.arrayBuffer();
	});

	it("returns 304 for If-Modified-Since in the future", async () => {
		const since = new Date(Date.now() + 3600_000).toUTCString();
		const res = await call("/sample/v0.1.0/imgs/pixel.png", { headers: { "if-modified-since": since } });
		expect(res.status).toBe(304);
	});
});

describe("markdown negotiation", () => {
	it("serves the .md export for Accept: text/markdown", async () => {
		const res = await call("/sample/v0.1.0/guide/quickstart/", { headers: { accept: "text/markdown" } });
		expect(res.status).toBe(200);
		expect(res.headers.get("content-type")).toBe("text/markdown; charset=utf-8");
		expect(res.headers.get("vary")).toBe("Accept");
		expect(await res.text()).toBe("# sample/v0.1.0/guide/quickstart.md\n");
	});

	it("maps a section index to <section>.md", async () => {
		const res = await call("/sample/v0.1.0/guide/", { headers: { accept: "text/markdown, text/plain;q=0.5" } });
		expect(await res.text()).toBe("# sample/v0.1.0/guide.md\n");
	});

	it("prefers HTML when the client also accepts it", async () => {
		const res = await call("/sample/v0.1.0/guide/quickstart/", { headers: { accept: "text/markdown, text/html" } });
		expect(res.headers.get("content-type")).toBe("text/html; charset=utf-8");
		expect(res.headers.get("vary")).toBe("Accept");
		await res.arrayBuffer();
	});

	it("falls back to HTML when a page has no export", async () => {
		// The fixture's reference section has no index page, so no reference.md.
		const res = await call("/sample/v0.1.0/reference/", { headers: { accept: "text/markdown" } });
		expect(res.status).toBe(200);
		expect(res.headers.get("content-type")).toBe("text/html; charset=utf-8");
		await res.arrayBuffer();
	});
});

describe("404s", () => {
	it("serves the build's own 404.html for a missing page in an existing version", async () => {
		const res = await call("/sample/v0.1.0/guide/missing/");
		expect(res.status).toBe(404);
		expect(res.headers.get("content-type")).toBe("text/html; charset=utf-8");
		expect(await res.text()).toContain("404 page of sample/v0.1.0/404.html");

		const asset = await call("/sample/main/imgs/missing.png");
		expect(asset.status).toBe(404);
		expect(await asset.text()).toContain("404 page of sample/main/404.html");
	});

	it("serves the built-in 404 elsewhere", async () => {
		for (const path of ["/sample/v9.9.9/guide/", "/onlymain/main/guide/missing/", "/nope/main/guide/", "/favicon.ico"]) {
			const res = await call(path);
			expect(res.status, path).toBe(404);
			const body = await res.text();
			expect(body, path).toContain("Page not found");
			expect(body, path).not.toContain("404 page of");
		}
	});
});

describe("manifests (C2)", () => {
	it("derives /<p>/_versions.json from markers", async () => {
		const res = await call("/sample/_versions.json");
		expect(res.status).toBe(200);
		expect(res.headers.get("content-type")).toBe("application/json; charset=utf-8");
		const cc = res.headers.get("cache-control")!;
		expect(Number(/max-age=(\d+)/.exec(cc)![1])).toBeLessThanOrEqual(60);
		expect(await res.json()).toEqual({
			default: "v0.1.0",
			versions: [
				{ version: "main", commit: "main-sha", built_at: "2026-10-01T00:00:00Z" },
				{ version: "v0.2.0-rc.1", commit: "v0.2.0-rc.1-sha", built_at: "2026-10-01T00:00:00Z" },
				{ version: "v0.1.0", commit: "a".repeat(40), built_at: "2026-10-01T12:00:00Z" },
			],
		});
	});

	it("sorts main first, then tags by descending semver", async () => {
		const body = (await (await call("/multi/_versions.json")).json()) as { default: string; versions: { version: string }[] };
		expect(body.default).toBe("v1.10.0");
		expect(body.versions.map((v) => v.version)).toEqual(["main", "v2.0.0-rc.1", "v1.10.0", "v1.2.0", "v0.9", "nightly"]);
	});

	it("hides versions and projects without a marker", async () => {
		expect((await call("/hidden/_versions.json")).status).toBe(404);
		const projects = (await (await call("/_projects.json")).json()) as { name: string }[];
		expect(projects.map((p) => p.name)).not.toContain("hidden");
	});

	it("derives /_projects.json from prefixes and _project.json", async () => {
		const res = await call("/_projects.json");
		expect(res.status).toBe(200);
		const projects = (await res.json()) as Record<string, unknown>[];
		expect(projects.map((p) => p.name)).toEqual(["evil", "multi", "onlymain", "prerel", "sample"]);
		expect(projects.find((p) => p.name === "sample")).toEqual({
			name: "sample",
			title: SAMPLE_PROJECT_JSON.title,
			description: SAMPLE_PROJECT_JSON.description,
			repo: SAMPLE_PROJECT_JSON.repo,
			default: "v0.1.0",
		});
		// No _project.json: falls back to the name.
		expect(projects.find((p) => p.name === "onlymain")).toEqual({
			name: "onlymain",
			title: "onlymain",
			description: "",
			repo: null,
			default: "main",
		});
	});
});

describe("landing page", () => {
	it("lists projects with links", async () => {
		const res = await call("/");
		expect(res.status).toBe(200);
		expect(res.headers.get("content-type")).toBe("text/html; charset=utf-8");
		const html = await res.text();
		expect(html).toContain('<a href="/sample/">Sample</a>');
		expect(html).toContain("A small sample project.");
		expect(html).not.toContain("hidden");
	});

	it("escapes everything that comes from R2", async () => {
		const html = await (await call("/")).text();
		expect(html).not.toContain("<script>");
		expect(html).not.toContain("<img");
		expect(html).toContain("&lt;script&gt;alert(&#39;title&#39;)&lt;/script&gt;");
		expect(html).toContain("&quot;&gt;&lt;img src=x onerror=alert(1)&gt; &amp; friends");
		// An invalid repo is dropped rather than linked.
		expect(html).not.toContain("alert('repo')");
		expect(EVIL_PROJECT_JSON.repo).toContain("<script>");
	});
});

describe("preview deployment", () => {
	it("adds X-Robots-Tag: noindex to every response", async () => {
		for (const path of ["/", "/_projects.json", "/sample/", "/sample/v0.1.0/guide/", "/sample/v0.1.0/imgs/pixel.png", "/nope/"]) {
			const res = await preview(path);
			expect(res.headers.get("x-robots-tag"), path).toBe("noindex");
			await res.arrayBuffer();
		}
		const prod = await call("/sample/v0.1.0/guide/");
		expect(prod.headers.get("x-robots-tag")).toBeNull();
		await prod.arrayBuffer();
	});

	it("disallows all crawling in robots.txt", async () => {
		expect(await (await preview("/robots.txt")).text()).toBe("User-agent: *\nDisallow: /\n");
		expect(await (await call("/robots.txt")).text()).toBe("User-agent: *\nAllow: /\n");
	});

	it("does not read _project.json", async () => {
		const projects = (await (await preview("/_projects.json")).json()) as { name: string; title: string }[];
		expect(projects.find((p) => p.name === "sample")?.title).toBe("sample");
	});
});
