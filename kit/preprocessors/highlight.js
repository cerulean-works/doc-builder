import hljs from "highlight.js";
import bash from "highlight.js/lib/languages/bash";

const COMMANDS = [
	"curl",
	"wget",
	"git",
	"gh",
	"docker",
	"podman",
	"python",
	"python3",
	"pip",
	"pip3",
	"uv",
	"uvx",
	"node",
	"npm",
	"npx",
	"pnpm",
	"yarn",
	"bun",
	"make",
	"cmake",
	"cargo",
	"go",
	"java",
	"ssh",
	"scp",
	"rsync",
	"tar",
	"unzip",
	"jq",
	"yq",
	"sed",
	"awk",
	"grep",
	"rg",
	"find",
	"sort",
	"ps",
	"kill",
	"kubectl",
	"helm",
	"terraform",
	"aws",
	"gcloud",
	"wrangler",
	"pytest",
	"ruff",
	"doc-builder",
	"flock",
	"flock-admin",
];

function shellGrammar(api) {
	const grammar = bash(api);
	const quoted = grammar.contains.filter((mode) => mode.className === "string");
	const variable = grammar.contains.find((mode) => mode.className === "variable");
	const substitution = quoted
		.flatMap((mode) => mode.contains ?? [])
		.find((mode) => mode.className === "subst");
	const assignment = {
		begin: [/\b[A-Za-z_]\w*/, /=/],
		beginScope: { 1: "attr", 2: "operator" },
		relevance: 0,
		starts: {
			end: /(?=[\s;&|)]|$)/,
			contains: [
				...quoted,
				variable,
				substitution,
				api.BACKSLASH_ESCAPE,
				{ scope: "string", match: /[^\s;&|)"'$`\\]+/, relevance: 0 },
			],
		},
	};
	grammar.keywords.built_in.push(...COMMANDS);
	substitution.keywords = grammar.keywords;
	grammar.contains.unshift(
		assignment,
		{ scope: "attribute", match: /(?<!\S)--?[A-Za-z][\w-]*/, relevance: 0 },
		{ scope: "operator", match: /&&|\|\||>>?|<<?|\|/, relevance: 0 }
	);
	return { grammar, assignment, variable };
}

hljs.registerLanguage("bash", (api) => shellGrammar(api).grammar);
hljs.registerAliases(["shellscript", "shell-script"], { languageName: "bash" });
hljs.registerLanguage("dotenv", (api) => {
	const { assignment } = shellGrammar(api);
	return {
		name: "Dotenv",
		aliases: ["env", "dot-env"],
		disableAutodetect: true,
		contains: [
			api.HASH_COMMENT_MODE,
			{ scope: "keyword", match: /\bexport(?=\s+[A-Za-z_]\w*=)/ },
			assignment,
		],
	};
});

// Python's interactive prompts are excluded from manual text selection and copying.
hljs.addPlugin({
	"after:highlight": (result) => {
		result.value = result.value
			.replace(/^(&gt;&gt;&gt;[ \t])/gm, '<span class="hljs-meta">$1</span>')
			.replace(/^(\.\.\.[ \t])/gm, '<span class="hljs-meta">$1</span>');
	},
});

export function highlightCode(source, language = "") {
	return language && hljs.getLanguage(language)
		? hljs.highlight(source, { language, ignoreIllegals: true }).value
		: hljs.highlightAuto(source).value;
}
