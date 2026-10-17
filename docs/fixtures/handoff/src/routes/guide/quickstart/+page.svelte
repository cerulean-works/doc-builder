<script lang="ts">
import Tip from "$lib/Tip.svelte";
import Added from "$lib/Added.svelte";
import Changed from "$lib/Changed.svelte";
import Deprecated from "$lib/Deprecated.svelte";
import CodeBlock from "$lib/CodeBlock.svelte";
import ExampleCodeBlock from "$lib/ExampleCodeBlock.svelte";
import Docstring from "$lib/Docstring.svelte";
import Heading from "$lib/Heading.svelte";
import MermaidChart from "$lib/MermaidChart.svelte";
import Youtube from "$lib/Youtube.svelte";
import Tabs from "$lib/Tabs.svelte";
import Tab from "$lib/Tab.svelte";
</script>

HF_DOC_BODY_START

# Quickstart

![A single pixel](/sample/v0.1.0/imgs/pixel.png)

## Build

Run `doc-builder build`. Braces like {x} and <tags> in text are escaped.

### Options

| Flag | Meaning |
|---|---|
| `--html` | Build HTML |

HF_DOC_BODY_END
