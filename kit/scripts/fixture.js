#!/usr/bin/env node
/**
 * Runs the kit against the golden handoff fixture (docs/fixtures/handoff), the same files
 * doc-builder stages into its temporary copy of the kit (docs/source/architecture.md, C5).
 *
 *   node scripts/fixture.js dev     # vite dev at http://localhost:5173/sample/v0.1.0/guide/
 *   node scripts/fixture.js build   # production build into ./build (vite build + pagefind)
 *
 * Staged files are removed again when the command exits, so they are never committed or
 * copied into doc-builder's temporary kit.
 */
import { spawn } from "node:child_process";
import { cpSync, existsSync, readdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const kitDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fixtureDir = resolve(kitDir, "../docs/fixtures/handoff");
const env = { ...process.env, DOCS_PROJECT: "sample", DOCS_VERSION: "v0.1.0" };

/** Files and folders that belong to the kit itself and must survive cleanup. */
const KEEP = {
	"src/routes": new Set(["+layout.svelte", "+layout.ts", "+error.svelte"]),
	static: new Set(["favicon.png"]),
};

function clean() {
	for (const [dir, keep] of Object.entries(KEEP)) {
		const path = join(kitDir, dir);
		if (!existsSync(path)) continue;
		for (const name of readdirSync(path)) {
			if (!keep.has(name)) rmSync(join(path, name), { recursive: true, force: true });
		}
	}
}

function stage() {
	clean();
	// src/routes/**, src/lib/generated/site.json and static/** (a copy of the committed site.json)
	cpSync(join(fixtureDir, "src"), join(kitDir, "src"), { recursive: true });
	cpSync(join(fixtureDir, "static"), join(kitDir, "static"), { recursive: true });
}

function run(command, args) {
	return new Promise((resolvePromise) => {
		const child = spawn(command, args, { cwd: kitDir, env, stdio: "inherit" });
		const forward = (signal) => child.kill(signal);
		process.on("SIGINT", forward);
		process.on("SIGTERM", forward);
		child.on("exit", (code, signal) => {
			process.off("SIGINT", forward);
			process.off("SIGTERM", forward);
			resolvePromise(code ?? (signal ? 1 : 0));
		});
	});
}

const mode = process.argv[2];
if (mode !== "dev" && mode !== "build") {
	console.error("usage: node scripts/fixture.js <dev|build>");
	process.exit(2);
}

const bin = (name) => join(kitDir, "node_modules", ".bin", name);

stage();
let code;
try {
	if (mode === "dev") {
		code = await run(bin("vite"), ["dev", ...process.argv.slice(3)]);
	} else {
		code = await run(bin("vite"), ["build"]);
		if (code === 0) code = await run(bin("pagefind"), ["--site", "build"]);
	}
} finally {
	clean();
}
process.exit(code);
