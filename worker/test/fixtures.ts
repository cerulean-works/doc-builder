/**
 * Seeds the in-memory R2 bucket. The `sample` project is exactly
 * docs/fixtures/r2-keys.txt (the contract's golden publish of `v0.1.0`), plus
 * a `main` build and a prerelease build of the same tree.
 */
import fixtureKeys from "../../docs/fixtures/r2-keys.txt?raw";

export const HASH = "abc123";

/** Keys from r2-keys.txt with `<hash>` filled in. */
export const SAMPLE_KEYS: string[] = fixtureKeys
	.split("\n")
	.map((line) => line.trim())
	.filter((line) => line !== "" && !line.startsWith("#"))
	.map((line) => line.replaceAll("<hash>", HASH));

export const SAMPLE_PROJECT_JSON = {
	name: "sample",
	title: "Sample",
	description: "A small sample project.",
	repo: "cerulean-works/sample",
};

export const EVIL_PROJECT_JSON = {
	name: "evil",
	title: "<script>alert('title')</script>",
	description: `"><img src=x onerror=alert(1)> & friends`,
	repo: `x"><script>alert('repo')</script>/y`,
};

function bodyFor(key: string): string {
	if (key.endsWith("/404.html")) return `<!doctype html><title>build 404</title><p>404 page of ${key}</p>`;
	if (key.endsWith(".html")) return `<!doctype html><title>${key}</title><p>page ${key}</p>`;
	if (key.endsWith(".md")) return `# ${key}\n`;
	if (key.endsWith("_project.json")) return JSON.stringify(SAMPLE_PROJECT_JSON);
	return `asset ${key}`;
}

/** Version subtree of the fixture (relative keys), reused for other versions and projects. */
const SAMPLE_TREE = SAMPLE_KEYS.filter((k) => k.startsWith("sample/v0.1.0/")).map((k) => k.slice("sample/v0.1.0/".length));

async function putBuild(bucket: R2Bucket, project: string, version: string, opts: { marker?: boolean; with404?: boolean } = {}) {
	const { marker = true, with404 = true } = opts;
	for (const rel of SAMPLE_TREE) {
		if (rel === "404.html" && !with404) continue;
		const key = `${project}/${version}/${rel}`;
		await bucket.put(key, bodyFor(key));
	}
	if (marker) {
		await bucket.put(`${project}/_versions/${version}`, "", {
			customMetadata: { commit: `${version}-sha`, built_at: "2026-10-01T00:00:00Z" },
		});
	}
}

export async function seed(bucket: R2Bucket): Promise<void> {
	// sample: the fixture verbatim, then main and a prerelease.
	for (const key of SAMPLE_KEYS) {
		if (key === "sample/_versions/v0.1.0") {
			await bucket.put(key, "", { customMetadata: { commit: "a".repeat(40), built_at: "2026-10-01T12:00:00Z" } });
		} else {
			await bucket.put(key, bodyFor(key));
		}
	}
	await putBuild(bucket, "sample", "main");
	await putBuild(bucket, "sample", "v0.2.0-rc.1");

	// Only prerelease tags: the default falls back to main.
	await putBuild(bucket, "prerel", "main");
	await putBuild(bucket, "prerel", "v1.0.0-beta.1");
	await putBuild(bucket, "prerel", "v2.0.0rc1");

	// No tags at all.
	await putBuild(bucket, "onlymain", "main", { with404: false });

	// Semver ordering (1.10 > 1.2) and a non-version tag.
	await putBuild(bucket, "multi", "main");
	await putBuild(bucket, "multi", "v1.2.0");
	await putBuild(bucket, "multi", "v1.10.0");
	await putBuild(bucket, "multi", "v2.0.0-rc.1");
	await putBuild(bucket, "multi", "v0.9");
	await putBuild(bucket, "multi", "nightly");

	// Malicious metadata for the landing-page escaping test.
	await putBuild(bucket, "evil", "main");
	await bucket.put("evil/_project.json", JSON.stringify(EVIL_PROJECT_JSON));

	// Uploaded but never published (no marker): invisible.
	await putBuild(bucket, "hidden", "main", { marker: false });
}
