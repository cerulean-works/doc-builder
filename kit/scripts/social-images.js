#!/usr/bin/env node
/** Generate PNG link previews from the prerendered HTML, using bundled fonts and artwork. */
import { readFile, readdir, mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { load } from "cheerio";
import satori from "satori";
import { Resvg } from "@resvg/resvg-js";

const kitDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const font = (pkg, file) =>
	readFile(join(dirname(require.resolve(`${pkg}/package.json`)), "files", file));
const fonts = await Promise.all([
	font("@fontsource/host-grotesk", "host-grotesk-latin-500-normal.woff"),
	font("@fontsource/geist", "geist-latin-400-normal.woff"),
]);
const logo = `data:image/png;base64,${(await readFile(join(kitDir, "src/lib/assets/logo.png"))).toString("base64")}`;

const text = (children, style = {}) => ({ type: "div", props: { style, children } });
const row = (children, style = {}) =>
	text(children, { display: "flex", alignItems: "center", ...style });

/** Render text through Satori so the PNG doesn't depend on system fonts or network access. */
export async function renderCard({ title, description, project, section, version }) {
	const svg = await satori(
		text(
			[
				row(
					[
						text(
							{
								type: "img",
								props: {
									src: logo,
									width: 56,
									height: 55,
									style: { position: "absolute", left: -5, top: -4 },
								},
							},
							{
								position: "relative",
								width: 46,
								height: 46,
								overflow: "hidden",
								borderRadius: "50%",
								display: "flex",
							}
						),
						text("Cerulean Docs", {
							width: 400,
							marginLeft: 16,
							fontSize: 30,
							fontFamily: "Host Grotesk",
							fontWeight: 500,
						}),
					],
					{ marginBottom: 56 }
				),
				text(project, {
					width: 1072,
					fontSize: 28,
					color: "#a8d4ff",
					marginBottom: 14,
					lineClamp: 1,
				}),
				text(title, {
					width: 1072,
					fontFamily: "Host Grotesk",
					fontWeight: 500,
					fontSize: title.length > 70 ? 54 : 64,
					letterSpacing: -2,
					lineHeight: 1.1,
					lineClamp: 3,
					height: 190,
				}),
				text(description, {
					width: 1072,
					fontSize: 25,
					lineHeight: 1.4,
					color: "#c1cbe0",
					lineClamp: 2,
					marginTop: 12,
				}),
				row(
					[
						text(section === "reference" ? "Reference" : "Guide"),
						text(/^pr_\d+$/.test(version) ? `Preview · PR #${version.slice(3)}` : version, {
							marginLeft: "auto",
							maxWidth: 800,
							lineClamp: 1,
						}),
					],
					{
						position: "absolute",
						left: 64,
						right: 64,
						bottom: 38,
						borderTop: "1px solid #415577",
						paddingTop: 20,
						fontSize: 21,
						color: "#a8d4ff",
					}
				),
			],
			{
				display: "flex",
				flexDirection: "column",
				boxSizing: "border-box",
				width: 1200,
				height: 630,
				backgroundColor: "#000000",
				color: "#f3f5f9",
				padding: "54px 64px",
				fontFamily: "Geist",
			}
		),
		{
			width: 1200,
			height: 630,
			fonts: [
				{ name: "Host Grotesk", data: fonts[0], weight: 500, style: "normal" },
				{ name: "Geist", data: fonts[1], weight: 400, style: "normal" },
			],
		}
	);
	return new Resvg(svg, { font: { loadSystemFonts: false } }).render().asPng();
}

async function* pages(dir) {
	for (const entry of await readdir(dir, { withFileTypes: true })) {
		const path = join(dir, entry.name);
		if (entry.isDirectory()) yield* pages(path);
		else if (entry.name === "index.html") yield path;
	}
}

export async function generatePreviews(buildDir = join(kitDir, "build")) {
	const site = JSON.parse(await readFile(join(kitDir, "src/lib/generated/site.json"), "utf8"));
	let count = 0;
	for await (const path of pages(buildDir)) {
		const $ = load(await readFile(path, "utf8"));
		// Redirect stubs and error pages deliberately don't advertise a social image.
		if (!$('meta[property="og:image"]').length) continue;
		const route = relative(buildDir, dirname(path)).split(sep).join("/");
		const title = $('meta[property="og:title"]').attr("content") ?? site.title;
		const png = await renderCard({
			title: title.replace(` · ${site.title} · Cerulean Docs`, ""),
			description: $('meta[property="og:description"]').attr("content") ?? site.description,
			project: site.title,
			section: route.split("/")[0],
			version: site.version,
		});
		const dest = join(buildDir, "social", `${route}.png`);
		await mkdir(dirname(dest), { recursive: true });
		await writeFile(dest, png);
		count++;
	}
	console.log(`Generated ${count} link preview images.`);
	return count;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	await generatePreviews();
}
