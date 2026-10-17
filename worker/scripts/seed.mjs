#!/usr/bin/env node
// Uploads one built version directory into the local R2 state that
// `wrangler dev` reads (.wrangler/state/v3), in the same order as
// publish_docs.yml: assets, then HTML, then `_project.json` (prod only), then
// the `<p>/_versions/<v>` marker with customMetadata {commit, built_at}.
//
//   pnpm run seed <dir> --project <p> --version <v> [--env preview] [--commit <sha>]
//
// <dir> is the version directory itself, i.e. `<build_dir>/<p>/<v>`.
import { readdir, readFile, stat } from "node:fs/promises";
import { join, relative, resolve, sep } from "node:path";
import { parseArgs } from "node:util";
import { getPlatformProxy } from "wrangler";

const USAGE = "usage: pnpm run seed <dir> --project <p> --version <v> [--env production|preview] [--commit <sha>]";
const PROJECT_RE = /^[A-Za-z0-9][\w-]*$/;
const VERSION_RE = /^[A-Za-z0-9][\w.+-]*$/;

// `pnpm run seed <args>` passes the `--` through; it would end option parsing.
const argv = process.argv.slice(2);
const { values, positionals } = parseArgs({
	args: argv[0] === "--" ? argv.slice(1) : argv,
	allowPositionals: true,
	options: {
		project: { type: "string" },
		version: { type: "string" },
		env: { type: "string", default: "production" },
		commit: { type: "string", default: "local" },
		help: { type: "boolean", short: "h" },
	},
});

if (values.help || positionals.length !== 1 || !values.project || !values.version) {
	console.error(USAGE);
	process.exit(values.help ? 0 : 2);
}
if (!["production", "preview"].includes(values.env)) {
	console.error(`--env must be production or preview, got ${values.env}`);
	process.exit(2);
}
if (!PROJECT_RE.test(values.project) || !VERSION_RE.test(values.version) || values.version === "latest") {
	console.error("invalid --project or --version");
	process.exit(2);
}

const dir = resolve(positionals[0]);
if (!(await stat(dir).catch(() => null))?.isDirectory()) {
	console.error(`not a directory: ${dir}`);
	process.exit(2);
}

async function walk(root) {
	const out = [];
	for (const entry of await readdir(root, { withFileTypes: true, recursive: true })) {
		if (entry.isFile()) out.push(relative(dir, join(entry.parentPath, entry.name)).split(sep).join("/"));
	}
	return out.sort();
}

const files = await walk(dir);
if (!files.includes("_project.json")) console.warn("warning: no _project.json in the build");
const project = values.project;
const version = values.version;
const preview = values.env === "preview";

// Mirrors publish_docs.yml. Preview never uploads _project.json.
const uploadable = files.filter((f) => !(preview && f === "_project.json"));
const assets = uploadable.filter((f) => !f.endsWith(".html"));
const html = uploadable.filter((f) => f.endsWith(".html"));

const configPath = resolve(import.meta.dirname, "..", "wrangler.jsonc");
// Same persistence directory as `wrangler dev` (.wrangler/state/v3 next to wrangler.jsonc).
const proxy = await getPlatformProxy({ configPath, environment: values.env, remoteBindings: false });
try {
	const bucket = proxy.env.DOCS;
	const prefix = `${project}/${version}/`;

	// Stale objects from a previous seed of this version go first (publish does `sync --delete`).
	let cursor;
	const stale = [];
	do {
		const page = await bucket.list({ prefix, cursor });
		stale.push(...page.objects.map((o) => o.key));
		cursor = page.truncated ? page.cursor : undefined;
	} while (cursor);
	const keep = new Set(uploadable.map((f) => prefix + f));
	const toDelete = stale.filter((k) => !keep.has(k));
	if (toDelete.length) await bucket.delete(toDelete);

	for (const [label, group] of [["assets", assets], ["html", html]]) {
		for (const rel of group) await bucket.put(prefix + rel, await readFile(join(dir, rel)));
		console.log(`${label}: ${group.length} object(s)`);
	}
	if (!preview && files.includes("_project.json")) {
		await bucket.put(`${project}/_project.json`, await readFile(join(dir, "_project.json")));
		console.log(`${project}/_project.json`);
	}
	await bucket.put(`${project}/_versions/${version}`, "", {
		customMetadata: { commit: values.commit, built_at: new Date().toISOString() },
	});
	console.log(`marker: ${project}/_versions/${version} (${values.env}, deleted ${toDelete.length} stale)`);
} finally {
	await proxy.dispose();
}
