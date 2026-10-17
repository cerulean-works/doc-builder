import { describe, expect, it } from "vitest";
import { buildVersionsManifest, listProjectNames, listVersions } from "../src/manifests";
import { compareVersions, isStableTag, pickDefault } from "../src/versions";

/**
 * A fake bucket whose `list` pages like R2: at most `pageSize` results per
 * call, and (like R2 with `include`) sometimes fewer than that while still
 * truncated.
 */
function pagingBucket(keys: string[], pageSize = 1000) {
	const calls: R2ListOptions[] = [];
	const bucket = {
		async list(options: R2ListOptions = {}) {
			calls.push(options);
			const prefix = options.prefix ?? "";
			const matching = keys.filter((k) => k.startsWith(prefix)).sort();
			let items: { key?: string; prefix?: string }[];
			if (options.delimiter) {
				const seen = new Set<string>();
				items = [];
				for (const k of matching) {
					const rest = k.slice(prefix.length);
					const i = rest.indexOf(options.delimiter);
					if (i === -1) items.push({ key: k });
					else {
						const p = prefix + rest.slice(0, i + 1);
						if (!seen.has(p)) {
							seen.add(p);
							items.push({ prefix: p });
						}
					}
				}
			} else {
				items = matching.map((key) => ({ key }));
			}
			const start = Number(options.cursor ?? 0);
			// Odd pages come back short to prove we loop on `truncated`, not on count.
			const size = calls.length % 2 ? Math.floor(pageSize / 3) : pageSize;
			const page = items.slice(start, start + size);
			const end = start + page.length;
			const truncated = end < items.length;
			return {
				objects: page
					.filter((i) => i.key)
					.map((i) => ({
						key: i.key!,
						customMetadata: options.include?.includes("customMetadata")
							? { commit: `sha-${i.key}`, built_at: "2026-10-01T00:00:00Z" }
							: undefined,
					})),
				delimitedPrefixes: page.filter((i) => i.prefix).map((i) => i.prefix!),
				truncated,
				...(truncated ? { cursor: String(end) } : {}),
			};
		},
	};
	return { bucket: bucket as unknown as R2Bucket, calls };
}

describe("manifest pagination", () => {
	it("lists more than 1000 version markers across pages", async () => {
		const keys = Array.from({ length: 2500 }, (_, i) => `big/_versions/pr_${i + 1}`);
		keys.push("big/_versions/main", "big/_versions/v1.0.0", "big/main/guide/index.html");
		const { bucket, calls } = pagingBucket(keys);
		const versions = await listVersions(bucket, "big");
		expect(versions).toHaveLength(2502);
		expect(calls.length).toBeGreaterThan(3);
		expect(calls.every((c) => c.prefix === "big/_versions/" && c.include?.includes("customMetadata"))).toBe(true);
		expect(versions.slice(0, 3).map((v) => v.version)).toEqual(["main", "v1.0.0", "pr_2500"]);
		expect(versions.at(-1)!.version).toBe("pr_1");
		expect(versions[0]).toEqual({ version: "main", commit: "sha-big/_versions/main", built_at: "2026-10-01T00:00:00Z" });

		const manifest = await buildVersionsManifest(bucket, "big");
		expect(manifest!.default).toBe("v1.0.0");
	});

	it("lists more than 1000 projects across pages", async () => {
		const keys: string[] = [];
		for (let i = 0; i < 1200; i++) {
			const name = `proj${String(i).padStart(4, "0")}`;
			keys.push(`${name}/_versions/main`, `${name}/main/guide/index.html`);
		}
		keys.push("_stray.json", "robots.txt");
		const { bucket, calls } = pagingBucket(keys);
		const names = await listProjectNames(bucket);
		expect(names).toHaveLength(1200);
		expect(names[0]).toBe("proj0000");
		expect(calls.every((c) => c.delimiter === "/")).toBe(true);
		expect(calls.length).toBeGreaterThan(1);
	});

	it("treats a project with no markers as absent", async () => {
		const { bucket } = pagingBucket(["ghost/main/guide/index.html"]);
		expect(await buildVersionsManifest(bucket, "ghost")).toBeNull();
	});
});

describe("version ordering", () => {
	it("recognises prereleases, including PEP 440 forms", () => {
		for (const t of ["v1.0.0", "1.2.3", "v2.0", "v1.0.0+build.5", "v1.0.0.post1"]) expect(isStableTag(t), t).toBe(true);
		for (const t of ["v1.0.0-rc.1", "v1.0.0rc1", "1.0.0a1", "v2.0.0b2", "v1.0.0.dev3", "v1.0.0-alpha", "main", "pr_3", "nightly"]) {
			expect(isStableTag(t), t).toBe(false);
		}
	});

	it("picks the highest stable tag, else main", () => {
		expect(pickDefault(["main", "v1.2.0", "v1.10.0", "v2.0.0-rc.1"])).toBe("v1.10.0");
		expect(pickDefault(["main", "v1.0.0rc1"])).toBe("main");
		expect(pickDefault(["main"])).toBe("main");
		expect(pickDefault(["1.0.0", "v1.0.1"])).toBe("v1.0.1");
		expect(pickDefault([])).toBeNull();
		// Preview bucket: no main, no tags. Pick the newest PR rather than a 404.
		expect(pickDefault(["pr_2", "pr_10"])).toBe("pr_10");
	});

	it("sorts main, tags (desc), other names, then PRs (desc)", () => {
		const sorted = ["pr_2", "v1.0.0", "nightly", "v1.0.0-rc.2", "main", "v1.0.0-rc.10", "pr_10", "v0.9.0"].sort(compareVersions);
		expect(sorted).toEqual(["main", "v1.0.0", "v1.0.0-rc.10", "v1.0.0-rc.2", "v0.9.0", "nightly", "pr_10", "pr_2"]);
	});
});
