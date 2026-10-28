import assert from "node:assert/strict";
import test from "node:test";
import { load } from "cheerio";
import { highlightCode } from "./highlight.js";

function render(source, language) {
	const html = highlightCode(source, language);
	const $ = load(`<pre><code>${html}</code></pre>`);
	assert.equal($("code").text(), source, "highlighting must preserve the original code");
	return $;
}

test("Bash highlights environment keys and entire unquoted values", () => {
	const $ = render(
		"FLOCK_WEB_URL=https://flock.example.com\nFLOCK_GOOGLE_CLIENT_ID=1234567890-abc123.apps.googleusercontent.com\nEMPTY=",
		"bash"
	);
	assert.deepEqual(
		$(".hljs-attr")
			.map((_, node) => $(node).text())
			.get(),
		["FLOCK_WEB_URL", "FLOCK_GOOGLE_CLIENT_ID", "EMPTY"]
	);
	assert.deepEqual(
		$(".hljs-string")
			.map((_, node) => $(node).text())
			.get(),
		["https://flock.example.com", "1234567890-abc123.apps.googleusercontent.com"]
	);
});

test("shell aliases highlight commands, flags and pipelines", () => {
	for (const language of ["bash", "sh", "zsh", "shellscript"]) {
		const $ = render("docker compose up -d && curl --fail https://example.com | jq .", language);
		assert.deepEqual(
			$(".hljs-built_in")
				.map((_, node) => $(node).text())
				.get(),
			["docker", "curl", "jq"]
		);
		assert.deepEqual(
			$(".hljs-attribute")
				.map((_, node) => $(node).text())
				.get(),
			["-d", "--fail"]
		);
		assert.deepEqual(
			$(".hljs-operator")
				.map((_, node) => $(node).text())
				.get(),
			["&&", "|"]
		);
	}
});

test("shell strings and comments keep their quoting and interpolation rules", () => {
	const $ = render("echo 'docker --fail $LITERAL' \"Bearer $TOKEN\" # docker --fail", "bash");
	assert.equal($(".hljs-variable").text(), "$TOKEN");
	assert.equal($(".hljs-attribute").length, 0);
	assert.equal($(".hljs-comment").text(), "# docker --fail");
	assert.equal($(".hljs-string").first().text(), "'docker --fail $LITERAL'");
});

test("assignments preserve quoted spaces, escaped spaces and command substitutions", () => {
	const $ = render('A="two words" B=two\\ words C=$(pwd)', "bash");
	assert.equal($(".hljs-attr").length, 3);
	assert.equal($(".hljs-subst .hljs-built_in").text(), "pwd");
});

test("dotenv and env fences support exports, comments and variable expansion", () => {
	for (const language of ["dotenv", "env", "dot-env"]) {
		const $ = render(
			'export HOST=https://example.com\nTOKEN="${SECRET}" # comment\nHASH=literal#value\nEMPTY=',
			language
		);
		assert.equal($(".hljs-keyword").text(), "export");
		assert.equal($(".hljs-attr").length, 4);
		assert.equal($(".hljs-variable").text(), "${SECRET}");
		assert.equal($(".hljs-comment").text(), "# comment");
		assert.ok(
			$(".hljs-string")
				.toArray()
				.some((node) => $(node).text() === "literal#value")
		);
	}
});

test("existing languages, plain text and HTML escaping remain intact", () => {
	assert.equal(render('print("<script>alert(1)</script>")', "python")("script").length, 0);
	assert.equal(render('{"count": 42}', "json")(".hljs-number").text(), "42");
	assert.equal(render("docker compose up -d", "plaintext")("span").length, 0);
	assert.equal(render("docker compose up -d", "text")("span").length, 0);
});
