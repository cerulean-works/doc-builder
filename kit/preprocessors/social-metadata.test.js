import assert from "node:assert/strict";
import test from "node:test";
import { mdsvexPreprocess } from "./mdsvex/index.js";

async function summary(body) {
	const { code } = await mdsvexPreprocess.markup({
		content: `HF_DOC_BODY_START\n\n${body}\n\nHF_DOC_BODY_END`,
		filename: "fixture/+page.svelte",
	});
	const literal = /export const description = (.*?);<\/script>/.exec(code)?.[1];
	assert.ok(literal);
	return { description: JSON.parse(literal), code };
}

test("preview descriptions use prose, skipping callouts, tables, code and images", async () => {
	const { description } = await summary(`# Title

> [!TIP]
> A callout is not the introduction.

\`\`\`python
print("not prose")
\`\`\`

| Heading |
| --- |
| Table |

![Artwork](picture.png)

Read **this guide** for [the API](https://example.com) and \`config\`.
The next line stays in the paragraph.

Later prose is excluded.`);
	assert.equal(
		description,
		"Read this guide for the API and config. The next line stays in the paragraph."
	);
});

test("descriptions are bounded and pages without prose permit the project fallback", async () => {
	assert.equal((await summary("# Title\n\n```bash\necho hi\n```")).description, "");
	const { description } = await summary(`# Title\n\n${"Long prose. ".repeat(60)}`);
	assert.ok(description.length <= 200);
	assert.ok(description.endsWith("…"));
});

test("description text cannot terminate its generated module script", async () => {
	const { description, code } = await summary(
		'# Title\n\nUse `</script>` and "quotes" with {braces} & Unicode café.'
	);
	assert.equal(description, "Use </script> and “quotes” with {braces} & Unicode café.");
	assert.ok(code.includes("\\u003c/script>"));
	assert.equal((code.match(/<\/script>/g) ?? []).length, 1);
});
