/**
 * Async string replace function.
 * src: https://github.com/dsblv/string-replace-async
 * @param {string} string
 * @param {RegExp} searchValue
 * @param {Function | string} replacer
 */
export async function replaceAsync(string, searchValue, replacer) {
	if (typeof replacer === "function") {
		// 1. Run fake pass of `replace`, collect values from `replacer` calls
		// 2. Resolve them with `Promise.all`
		// 3. Run `replace` with resolved values
		const values = [];
		String.prototype.replace.call(string, searchValue, function () {
			values.push(replacer.apply(undefined, arguments));
			return "";
		});
		const resolvedValues = await Promise.all(values);
		return String.prototype.replace.call(string, searchValue, function () {
			return resolvedValues.shift();
		});
	}
	return String.prototype.replace.call(string, searchValue, replacer);
}

/**
 * Render escaped characters like `<`, `{`, '#'.
 * used for Doc
 * @param {string} code
 */
export function renderSvelteChars(code) {
	return code
		.replace(/&amp;lcub;/g, "{")
		.replace(/&amp;lt;/g, "<")
		.replace(/&amp;num;/g, "#");
}

/**
 * Create a regex that captures html-like opening and closing tag and its contents.
 * used for parsing hf custom syntax
 * example: generateTagRegex("inferenceSnippet", true) -> /<inferenceSnippet>(.*?)<\/inferenceSnippet>/msg
 * @param {string} tag - The name of the tag to match content within.
 * @param {boolean} [global=false] - Whether to create a global pattern that matches all occurrences.
 * @returns {RegExp} - The generated RegExp pattern.
 */
export function generateTagRegex(tag, global = false) {
	const flags = global ? "msg" : "ms";
	const pattern = new RegExp(`<${tag}>(.*?)<\\/${tag}>`, flags);
	return pattern;
}

/**
 * Create a regex that captures html-like opening and closing tag with attribute "id" and its contents.
 * used for parsing hf custom syntax
 * example: generateTagRegex("inferenceSnippet", true) -> /<inferenceSnippet\s+id=["'](.+)["']\s*>(.*?)<\/inferenceSnippet>/msg
 * @param {string} tag - The name of the tag to match content within.
 * @param {boolean} [global=false] - Whether to create a global pattern that matches all occurrences.
 * @returns {RegExp} - The generated RegExp pattern.
 */
export function generateTagRegexWithId(tag, global = false) {
	const flags = global ? "msg" : "ms";
	const pattern = new RegExp(`<${tag}\\s+id=["'](.+?)["']\\s*>(.*?)<\\/${tag}>`, flags);
	return pattern;
}

/**
 * Swaps fenced code blocks out of `content` for placeholders, so tag-rewriting preprocessors leave
 * code examples of the same syntax alone. A block only closes on a fence of the same character that
 * is at least as long, so a four-backtick block can show three-backtick fences.
 * @param {string} content
 * @returns {{ masked: string, restore: (text: string) => string }}
 */
export function maskCodeBlocks(content) {
	const saved = [];
	const out = [];
	let block = [];
	let fence = null;
	for (const line of content.split("\n")) {
		const marker = /^\s*(`{3,}|~{3,})/.exec(line)?.[1];
		if (fence === null) {
			if (marker) {
				fence = marker;
				block = [line];
			} else {
				out.push(line);
			}
			continue;
		}
		block.push(line);
		if (
			marker &&
			marker[0] === fence[0] &&
			marker.length >= fence.length &&
			line.trim() === marker
		) {
			saved.push(block.join("\n"));
			out.push(`@@doc-builder-code-${saved.length - 1}@@`);
			fence = null;
		}
	}
	if (fence !== null) out.push(...block);
	const masked = out.join("\n");
	const restore = (text) =>
		text.replace(/@@doc-builder-code-(\d+)@@/g, (_, index) => saved[Number(index)]);
	return { masked, restore };
}
