/**
 * Server-rendered pages: the landing page at `/` and the built-in 404.
 * Styled with the Cerulean tokens (design-system.md): Evening by default,
 * Daylight under `prefers-color-scheme: light`, flat surfaces, radius 0.
 *
 * Everything interpolated into markup goes through `escapeHtml`; project
 * metadata comes from R2 and is written by builds, so it is untrusted.
 */
import type { ProjectEntry } from "./manifests";

const ESCAPES: Record<string, string> = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	'"': "&quot;",
	"'": "&#39;",
};

export function escapeHtml(value: unknown): string {
	return String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]!);
}

const STYLE = `
:root {
	color-scheme: dark light;
	--canvas: #10254b; --text: #f4f2e9; --muted: #c1cbe0; --link: #a8d4ff;
	--focus: #a8d4ff; --rule: #415577; --selection: #235fa2;
	--editorial: "Newsreader", Georgia, "Times New Roman", serif;
	--utility: "DM Sans", Arial, system-ui, sans-serif;
}
@media (prefers-color-scheme: light) {
	:root {
		--canvas: #fcfbf6; --text: #172a50; --muted: #4b5d79; --link: #145a9a;
		--focus: #1768af; --rule: #cdd3db; --selection: #cce7fb;
	}
}
* { box-sizing: border-box; border-radius: 0; box-shadow: none; }
html { background: var(--canvas); color: var(--text); }
body { margin: 0; font: 400 17px/1.45 var(--utility); }
::selection { background: var(--selection); }
main { max-width: 46rem; margin: 0 auto; padding: 96px 24px 128px; }
h1 { font: 400 clamp(40px, 6vw, 52px)/1.12 var(--editorial); letter-spacing: -0.02em; margin: 0 0 24px; }
.lede { font: 400 24px/1.4 var(--editorial); color: var(--muted); margin: 0 0 64px; }
ul { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--rule); }
li { padding: 32px 0; border-bottom: 1px solid var(--rule); }
h2 { font: 400 28px/1.18 var(--editorial); letter-spacing: -0.01em; margin: 0 0 8px; }
p { margin: 0; }
.desc { color: var(--text); }
.meta { margin-top: 12px; font-size: 15px; color: var(--muted); }
a { color: var(--link); text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
h2 a { color: var(--text); text-decoration: none; }
h2 a:hover { color: var(--link); text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; }
code { font: 15px/1.6 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.empty { color: var(--muted); padding: 32px 0; border-bottom: 1px solid var(--rule); }
`;

function page(title: string, body: string, noindex: boolean): string {
	return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
${noindex ? '<meta name="robots" content="noindex">\n' : ""}<title>${escapeHtml(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">
<style>${STYLE}</style>
</head>
<body>
<main>
${body}
</main>
</body>
</html>
`;
}

export function renderLanding(siteName: string, projects: ProjectEntry[], preview: boolean): string {
	const items = projects.length
		? `<ul>\n${projects
				.map((p) => {
					const href = `/${encodeURIComponent(p.name)}/`;
					const desc = p.description ? `\n<p class="desc">${escapeHtml(p.description)}</p>` : "";
					const repo = p.repo
						? ` · <a href="https://github.com/${escapeHtml(p.repo)}">${escapeHtml(p.repo)}</a>`
						: "";
					return `<li>\n<h2><a href="${escapeHtml(href)}">${escapeHtml(p.title)}</a></h2>${desc}\n<p class="meta"><code>${escapeHtml(p.default)}</code>${repo}</p>\n</li>`;
				})
				.join("\n")}\n</ul>`
		: `<p class="empty">No documentation has been published yet.</p>`;
	const lede = preview
		? "Pull request previews. These builds are temporary and expire after 30 days."
		: "Documentation for Cerulean projects.";
	return page(siteName, `<h1>${escapeHtml(siteName)}</h1>\n<p class="lede">${escapeHtml(lede)}</p>\n${items}`, preview);
}

export function renderError(siteName: string, status: number, message: string, preview: boolean): string {
	return page(
		`${status} · ${siteName}`,
		`<h1>${escapeHtml(message)}</h1>\n<p class="lede">${status === 404 ? "There is no page at this address." : "This address can't be served."}</p>\n<p><a href="/">Back to ${escapeHtml(siteName)}</a></p>`,
		preview,
	);
}
