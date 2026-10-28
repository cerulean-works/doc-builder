import { highlightCode } from "../highlight.js";
import { mdsvex } from "mdsvex";
import katex from "katex";
import { visit, SKIP } from "unist-util-visit";
import htmlTags from "html-tags";
import { readdir } from "fs/promises";
import path from "path";
import * as cheerio from "cheerio";
import { renderSvelteChars } from "../utils.js";

/**
 * inside `<code>` html elements, we need to replace `&amp;` with `&`
 * to correctly render escaped characters like `<`, `{`, etc.
 * used for Doc
 * @param {string} code
 */
function renderCode(code) {
	const REGEX_CODE_TAG = /<code>(((?!<code>).)*)<\/code>/gms;
	return code.replace(
		REGEX_CODE_TAG,
		(_, group1) => `<code>${group1.replace(/&amp;/gm, "&")}</code>`
	);
}

/**
 * Svelte 5 raises a compile error (`node_invalid_placement`) when `<tr>` is a
 * direct child of `<table>`, because browsers auto-insert `<tbody>` during
 * parsing, which would break hydration. Raw-HTML tables in doc markdown
 * commonly omit `<tbody>` (e.g. `<table><tr>...`), so add it explicitly —
 * the resulting DOM is identical to what browsers produced for the old output.
 * @param {string} code
 */
function wrapTableRowsInTbody(code) {
	return code
		.replace(/(<table\b[^>]*>)(\s*)(<tr\b)/g, "$1$2<tbody>$3")
		.replace(/(<\/tr>)(\s*)(<\/table>)/g, "$1</tbody>$2$3");
}

function addFullWidthClassToTables(code) {
	return code.replace(/<table\b([^>]*)>/g, (match, attrs) => {
		if (attrs.includes('class="')) {
			// Add to existing class
			return match.replace(/class="([^"]*)"/, 'class="$1 full-width"');
		} else if (attrs.includes("class='")) {
			// Add to existing class (single quotes)
			return match.replace(/class='([^']*)'/, "class='$1 full-width'");
		} else {
			// Add new class attribute
			return `<table${attrs} class="full-width">`;
		}
	});
}

const WRAP_CODE_BLOCKS_FLAG = "<!-- WRAP CODE BLOCKS -->";
const STRETCH_TABLES_FLAG = "<!-- STRETCH TABLES -->";
let wrapCodeBlocks = false;
let stretchTables = false;

export const mdsvexPreprocess = {
	markup: async ({ content, filename }) => {
		if (filename.endsWith("+page.svelte")) {
			const markedKatex = {};
			wrapCodeBlocks = content.includes(WRAP_CODE_BLOCKS_FLAG);
			stretchTables = content.includes(STRETCH_TABLES_FLAG);
			content = markKatex(content, markedKatex);
			content = escapeSvelteConditionals(content);
			const processed = await _mdsvexPreprocess.markup({ content, filename });
			processed.code = renderKatex(processed.code, markedKatex);
			processed.code = renderCode(processed.code, filename);
			processed.code = wrapTableRowsInTbody(processed.code);
			if (stretchTables) {
				processed.code = addFullWidthClassToTables(processed.code);
			}
			// Keep native table layout at the column width; overflow belongs to a wrapper.
			processed.code = processed.code
				.replace(
					/<table\b/g,
					'<div class="table-scroll" tabindex="0" role="region" aria-label="Table"><table'
				)
				.replace(/<\/table>/g, "</table></div>");
			return processed;
		}
		return { code: content };
	},
};

/**
 * Latex support in mdsvex
 * @param {string} content
 * @param {Record<any, any>} markedKatex
 */
function markKatex(content, markedKatex) {
	const REGEX_LATEX_DISPLAY = /\n\$\$([\s\S]+?)\$\$/g;
	const REGEX_LATEX_INLINE = /\s\\\\\(([\s\S]+?)\\\\\)/g;
	// Match $...$ with whitespace boundaries to avoid matching in HTML/code
	const REGEX_LATEX_INLINE_DOLLAR = /(\s)(\$)([^$\n`<>]+?)(\$)(\s)/g;
	let counter = 0;
	return content
		.replace(REGEX_LATEX_DISPLAY, (_, tex) => {
			const displayMode = true;
			const marker = `KATEXPARSE${counter++}MARKER`;
			markedKatex[marker] = { tex, displayMode };
			return marker;
		})
		.replace(REGEX_LATEX_INLINE, (_, tex) => {
			const displayMode = false;
			const marker = `KATEXPARSE${counter++}MARKER`;
			markedKatex[marker] = { tex, displayMode };
			return marker;
		})
		.replace(
			REGEX_LATEX_INLINE_DOLLAR,
			(match, spaceBefore, _openDollar, tex, _closeDollar, spaceAfter) => {
				const displayMode = false;
				const marker = `KATEXPARSE${counter++}MARKER`;
				markedKatex[marker] = { tex, displayMode };
				return spaceBefore + marker + spaceAfter;
			}
		);
}

function renderKatex(code, markedKatex) {
	return code.replace(/KATEXPARSE[0-9]+MARKER/g, (marker) => {
		let { tex, displayMode } = markedKatex[marker];
		tex = tex.replaceAll("&#123;", "{");
		tex = tex.replaceAll("&#60;", "<");
		const html = katex.renderToString(renderSvelteChars(tex), {
			displayMode,
			throwOnError: false,
		});
		if (html.includes(`katex-error`)) {
			throw new Error(`[KaTeX] Error while parsing markdown\n ${html}`);
		}
		return `{@html ${JSON.stringify(html)}}`;
	});
}

/**
 * Names of the components doc content may use: the top-level `.svelte` files of `src/lib`.
 * Subdirectories (e.g. `src/lib/chrome`, the site layout) are not doc components.
 * @param {string} startDir
 */
async function findSvelteComponentNames(startDir) {
	const files = await readdir(startDir, { withFileTypes: true });
	return files
		.filter((file) => file.isFile() && path.extname(file.name) === ".svelte")
		.map((file) => path.basename(file.name, ".svelte"));
}

const dirPath = "./src/lib";
const svelteTags = await findSvelteComponentNames(dirPath);
const validTags = [...htmlTags, ...svelteTags];

// The doc body (the only region whose text is escaped) sits between these markers (C5).
const BODY_START_MARKERS = ["HF_DOC_BODY_START", "<!--HF DOCBUILD BODY START-->"];
const BODY_END_MARKERS = ["HF_DOC_BODY_END", "<!--HF DOCBUILD BODY END-->"];
const isMarker = (value) => BODY_START_MARKERS.includes(value) || BODY_END_MARKERS.includes(value);

function addToTree(tree, node) {
	if (tree.length === 0 || tree[tree.length - 1].depth >= node.depth) {
		tree.push(node);
	} else {
		const sections = tree[tree.length - 1].sections || [];
		tree[tree.length - 1].sections = addToTree(sections, node);
	}
	return tree;
}

function getTitleText(node) {
	if (!node.children || node.children.length === 0) {
		return node.value ? node.value.trim() : "";
	}

	return node.children
		.map((child) => getTitleText(child))
		.join(" ")
		.trim();
}

/**
 * Every page exports `metadata`: a JSON string of its H1 heading tree, or `null` when the page
 * has no headings (docs/source/architecture.md, C5). `+page.ts` reads it with `JSON.parse(metadata)`.
 * The value is emitted as a JS string literal; `<` is escaped so a heading can never close the
 * surrounding `<script>` element.
 * @param {unknown} headingTree
 */
export function metadataScript(headingTree) {
	const literal = JSON.stringify(JSON.stringify(headingTree ?? null)).replaceAll("<", "\\u003c");
	return `<script module>export const metadata = ${literal};</script>`;
}

function treeVisitor() {
	// Doc-body marker offsets, recomputed per document in transform() (see isWithinDocBody).
	let bodyStartOffset = -1;
	let bodyEndOffset = Infinity;

	return transform;

	function transform(tree) {
		let headings = [];
		visit(tree, "heading", (node, index, parent) => {
			const depth = node.depth;
			let title = getTitleText(node);
			let local;
			const match = title.match(/\[\s(.*?)\s\]$/);
			if (match && match[1]) {
				local = match[1];
				title = title.replace(match[0], "").trim();
			} else {
				local = title
					.trim()
					.toLowerCase()
					.replace(/\s+/g, "-") // Replace spaces with hyphens
					.replace(/[^\p{L}\p{N}-]+/gu, ""); // Keep letters, numbers, and hyphens only
			}
			headings = addToTree(headings, { title, local, sections: [], depth });

			// Create a svelte node (in remark grammar, the type is "html")
			const svelteNode = {
				type: "html",
				value: `<Heading title="${title.replaceAll(
					"{",
					"&#123;"
				)}" local="${local}" headingTag="h${depth}"/>`,
			};
			// Replace the old node with the new Svelte node
			parent.children[index] = svelteNode;
		});
		// The doc-body region is delimited by the HF_DOC_BODY markers. Locate them up front and
		// compare source offsets, so every visitor below agrees on what is inside the body
		// regardless of traversal order.
		bodyStartOffset = -1;
		bodyEndOffset = Infinity;
		visit(tree, ["text", "html"], (node) => {
			if (BODY_START_MARKERS.includes(node.value)) {
				bodyStartOffset = node.position?.start?.offset ?? -1;
			}
			if (BODY_END_MARKERS.includes(node.value)) {
				bodyEndOffset = Math.min(bodyEndOffset, node.position?.start?.offset ?? Infinity);
			}
		});
		// Drop the markers themselves (a marker on its own line is a one-child paragraph).
		visit(tree, ["paragraph", "text", "html"], (node, index, parent) => {
			if (node.type === "paragraph") {
				const [child] = node.children;
				if (node.children.length === 1 && child.type === "text" && isMarker(child.value)) {
					parent.children.splice(index, 1);
					return [SKIP, index];
				}
			} else if (node.value === "HF_DOC_BODY_START" || node.value === "HF_DOC_BODY_END") {
				node.value = "";
			}
		});

		visit(tree, "text", onText);
		visit(tree, "html", onHtml);
		visit(tree, "link", onLink);
		visit(tree, "image", onLink);
		visit(tree, "blockquote", onBlockquote);

		tree.children.unshift({
			type: "html",
			value: metadataScript(headings[0] ?? null),
		});
	}

	/** Whether `node` comes from the source between the doc-body markers. */
	function isWithinDocBody(node) {
		const offset = node.position?.start?.offset;
		return (
			bodyStartOffset !== -1 &&
			offset !== undefined &&
			offset > bodyStartOffset &&
			offset < bodyEndOffset
		);
	}

	function onText(node) {
		if (!isWithinDocBody(node)) {
			return;
		}
		node.value = node.value.replaceAll("{", "&#123;");
		node.value = node.value.replaceAll("<", "&#60;");
	}

	/**
	 * A link's URL is stored on the mdast node's `url` property, not in a
	 * child text node, so `onText` never escapes curly braces inside it.
	 * mdsvex then emits the raw braces into the `href`/`src` attribute of the
	 * generated HTML, where Svelte 5 interprets `{...}` as an expression.
	 * During prerendering this throws `ReferenceError: <name> is not defined`
	 * (e.g. for URLs containing OpenAPI path params like `{username}`).
	 * Escaping `{` as an HTML entity keeps the rendered URL identical while
	 * making it inert to the Svelte compiler.
	 */
	function onLink(node) {
		if (!isWithinDocBody(node)) {
			return;
		}
		if (typeof node.url === "string") {
			node.url = node.url.replaceAll("{", "&#123;");
		}
		if (typeof node.title === "string") {
			node.title = node.title.replaceAll("{", "&#123;");
		}
	}

	function onHtml(node) {
		if (!isWithinDocBody(node)) {
			return;
		}
		const RE_TAG_NAME = /<\/?(\w+)/;
		const match = node.value.match(RE_TAG_NAME);
		const REGEX_VALID_START_END_TAG = /^<(\w+)[^>]*>.*<\/\1>$/s;
		if (match) {
			const tagName = match[1];
			if (!validTags.includes(tagName)) {
				node.value = node.value.replaceAll("<", "&#60;");
			} else if (htmlTags.includes(tagName) && REGEX_VALID_START_END_TAG.test(node.value.trim())) {
				const $ = cheerio.load(node.value);
				// Escape "{" in every text node. The serializer would encode an entity's "&", so
				// substitute a placeholder and swap in "&#123;" after serializing.
				const LCURLY = "__HF_DOC_LCURLY__";
				$("*")
					.contents()
					.each((index, element) => {
						if (element.type === "text") {
							element.data = element.data.replaceAll("{", LCURLY);
						}
					});
				// Update the remark HTML node with the modified HTML
				node.value = $("body").html().replaceAll(LCURLY, "&#123;");
			}
		}
	}

	function onBlockquote(node) {
		// use github-like admonition syntax
		// see https://github.com/orgs/community/discussions/16925
		const { children: childrenLevel1 } = node;
		if (!childrenLevel1.length || childrenLevel1[0].type !== "paragraph") {
			return;
		}

		const { children: childrenLevel2 } = childrenLevel1[0];
		if (!childrenLevel2.length || childrenLevel2[0].type !== "linkReference") {
			return;
		}

		const TIP_MARKERS = ["note", "tip", "important", "warning", "caution"];
		const { identifier } = childrenLevel2[0];
		if (typeof identifier !== "string") {
			return;
		}
		const markerWithBang = identifier.startsWith("!") ? identifier.slice(1) : identifier;
		const marker = markerWithBang.toLowerCase();
		if (!TIP_MARKERS.includes(marker)) {
			return;
		}

		childrenLevel1[0].children = childrenLevel1[0].children.slice(1);
		const [firstChild] = childrenLevel1[0].children;
		if (firstChild && firstChild.type === "text") {
			firstChild.value = firstChild.value.replace(/^\s+/u, "");
			if (!firstChild.value.length) {
				childrenLevel1[0].children.shift();
			}
		}
		if (!childrenLevel1[0].children.length) {
			node.children = node.children.slice(1);
		}

		node.data = node.data || {};
		node.data.hProperties = node.data.hProperties || {};
		const existingClasses = node.data.hProperties.className || [];
		const normalizedClasses = Array.isArray(existingClasses)
			? existingClasses
			: typeof existingClasses === "string"
				? existingClasses.split(/\s+/u).filter(Boolean)
				: [];
		node.data.hProperties.className = Array.from(new Set([...normalizedClasses, marker]));
	}
}

const _mdsvexPreprocess = mdsvex({
	remarkPlugins: [treeVisitor],
	extensions: ["svelte"],
	highlight: {
		highlighter: function (code, lang) {
			const REGEX_CODE_INPUT = /^(>>>\s|\.\.\.\s)/m;
			const base64 = (val) => btoa(encodeURIComponent(val));
			const escape = (source) =>
				source
					.replace(/\\/g, "\\\\")
					.replace(/`/g, "\\`")
					.replace(/}/g, "\\}")
					.replace(/\$/g, "\\$");
			const safeLang = lang && /^[\w-]+$/.test(lang) ? lang : "";
			// legacy PyTorch/TensorFlow split blocks render as consecutive code blocks
			const REGEX_FRAMEWORKS_SPLIT = /\s*===(?:PT-TF|STRINGAPI-READINSTRUCTION)-SPLIT===\s*/m;

			// Handle mermaid diagrams
			if (lang === "mermaid") {
				return `
	<MermaidChart code="${base64(code)}" />`;
			}

			code = renderSvelteChars(code);
			return code
				.split(REGEX_FRAMEWORKS_SPLIT)
				.map((group) => {
					const highlighted = highlightCode(group, lang);
					// filter out outputs if the code was generated interactively
					// `>>> for i in range(5):` becomes `for i in range(5):`
					if (group.match(REGEX_CODE_INPUT)) {
						group = group
							.split("\n")
							.filter((line) => line.match(REGEX_CODE_INPUT) || !line)
							.map((line) => line.replace(REGEX_CODE_INPUT, ""))
							.join("\n");
					}
					return `
	<CodeBlock
		code={\`${base64(group)}\`}
		highlighted={\`${escape(highlighted)}\`}
		lang="${safeLang}"
		wrap={${wrapCodeBlocks}}
	/>`;
				})
				.join("\n");
		},
	},
});

function escapeSvelteConditionals(code) {
	const REGEX_SVELTE_IF_START = /(\{#if[^}]+\})/g;
	const SVELTE_ELSE = "{:else}";
	const SVELTE_IF_END = "{/if}";
	code = code.replace(REGEX_SVELTE_IF_START, "\n\n$1\n\n");
	code = code.replaceAll(SVELTE_ELSE, `\n\n${SVELTE_ELSE}\n\n`);
	code = code.replaceAll(SVELTE_IF_END, `\n\n${SVELTE_IF_END}\n\n`);
	return code;
}
