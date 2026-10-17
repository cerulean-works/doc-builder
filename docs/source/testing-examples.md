# Testing code examples

Code examples go stale silently. doc-builder lets you mark Python examples as **runnable** and run them as tests with pytest. A broken example then fails CI instead of confusing a reader.

## Marking a block as runnable

Add `runnable` (or `runnable:<label>`) after the language of a `py` or `python` fence:

````md
```py runnable:quickstart
from flock import Flock

flock = Flock(size=2)
result = flock.run("count to three")
assert result.ok  # doc-builder: ignore-bare-assert
```
````

- The label names the test, and appears in failures and warnings.
- In the rendered page the marker is removed, so readers see an ordinary code block.

### Hiding setup lines

Lines a reader doesn't need can still run. Add `# doc-builder: hide` to a line to remove it from the rendered page, or put it on a line that opens a block to hide the whole block:

````md
```py runnable:quickstart
import os  # doc-builder: hide
os.environ["FLOCK_OFFLINE"] = "1"  # doc-builder: hide
from flock import Flock
```
````

### Continuing a block

Use `:2`, `:3`, … to continue an earlier block in the same namespace, so later snippets can build on earlier setup:

````md
```py runnable:agents
flock = Flock(size=2)
```

Some explanation in between.

```py runnable:agents:2
flock.run("hello")
```
````

### Skipping or marking tests

`# pytest-decorator:` lines apply decorators to the generated test. Skip-style decorators (raising `unittest.SkipTest`) are reported as skips:

````md
```py runnable:gpu_example
# pytest-decorator: flock.testing.require_gpu, flock.testing.slow
flock = Flock(size=64, device="cuda")
```
````

These lines are removed from both the executed code and the rendered page.

## Running them

Installing doc-builder registers a pytest plugin. Point pytest at Markdown files or folders:

```bash
pytest -q docs/source/quickstart.md
pytest -q docs/source/
```

The plugin:
- creates one test per runnable block, grouping continuations with their first block
- applies the decorators
- reports failures with the Markdown file and the code of the block

If you'd rather keep doc tests in your Python test suite, subclass `DocIntegrationTest`:

```python
from pathlib import Path

from doc_builder.testing import DocIntegrationTest


class QuickstartDocTest(DocIntegrationTest):
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "source" / "quickstart.md"
```

Each runnable block becomes a test method: `runnable:quickstart` becomes `test_quickstart`.

> [!WARNING]
> Both approaches run the code with `exec`. Only run docs your repository controls.

## Bare `assert` warnings

A bare `assert` in an example shows readers test code instead of the output they'd see. Build with `--emit-warning` to flag them:

```bash
doc-builder build flock docs/source --emit-warning
```

Each one is reported with its file and line, as a GitHub annotation when running in Actions.
- To silence a deliberate one, add `# doc-builder: ignore-bare-assert`. The comment is removed from the rendered page.
- Lines hidden with `# doc-builder: hide` are never reported.

## In CI

Run pytest on your docs alongside your other tests, for example in your existing test workflow:

```yaml
- name: Test documentation examples
  run: pytest -q docs/source/
```
