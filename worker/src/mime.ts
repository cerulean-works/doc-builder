/**
 * Content types by extension. The Worker decides the type itself rather than
 * trusting what the uploader guessed (`aws s3` maps `.md` and `.inv` poorly),
 * and only falls back to the stored httpMetadata for unknown extensions.
 */
const TYPES: Record<string, string> = {
	html: "text/html; charset=utf-8",
	htm: "text/html; charset=utf-8",
	md: "text/markdown; charset=utf-8",
	txt: "text/plain; charset=utf-8",
	css: "text/css; charset=utf-8",
	js: "text/javascript; charset=utf-8",
	mjs: "text/javascript; charset=utf-8",
	json: "application/json; charset=utf-8",
	map: "application/json; charset=utf-8",
	xml: "application/xml; charset=utf-8",
	wasm: "application/wasm",
	svg: "image/svg+xml",
	png: "image/png",
	jpg: "image/jpeg",
	jpeg: "image/jpeg",
	gif: "image/gif",
	webp: "image/webp",
	avif: "image/avif",
	ico: "image/x-icon",
	woff: "font/woff",
	woff2: "font/woff2",
	ttf: "font/ttf",
	otf: "font/otf",
	mp4: "video/mp4",
	webm: "video/webm",
	pdf: "application/pdf",
	csv: "text/csv; charset=utf-8",
	ipynb: "application/json; charset=utf-8",
	// pagefind index chunks are binary
	pf_meta: "application/octet-stream",
	pf_index: "application/octet-stream",
	pf_fragment: "application/octet-stream",
	pagefind: "application/octet-stream",
	// Sphinx inventory (zlib-compressed after a text header)
	inv: "application/octet-stream",
};

export function extensionOf(key: string): string | null {
	const last = key.slice(key.lastIndexOf("/") + 1);
	const dot = last.lastIndexOf(".");
	if (dot <= 0 || dot === last.length - 1) return null;
	return last.slice(dot + 1).toLowerCase();
}

export function contentTypeFor(key: string, stored?: string): string {
	const ext = extensionOf(key);
	return (ext && TYPES[ext]) || stored || "application/octet-stream";
}
