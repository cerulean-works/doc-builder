# Documenting a Python API

For Python packages, doc-builder imports the package while it builds and turns docstrings into reference pages. This page covers how to do that. The exact docstring format is in [Docstring format](docstrings).

## Autodoc

Put `[[autodoc]]` followed by an object's import path on a line of its own:

```md
# Main classes

## Flock

[[autodoc]] Flock

## Helpers

[[autodoc]] utils.load_config
```

Paths are relative to the package, so with the package `flock`, `Flock` means `flock.Flock` and `utils.load_config` means `flock.utils.load_config`.

The rendered entry shows:
- the signature
- the parameters, return value and raised exceptions
- a **source** link to the exact line on GitHub, at the commit that was built

For a class, every public method that has a docstring is documented too. To choose the methods, list them under the marker:

```md
[[autodoc]] Flock
    - run
    - stop
```

To add methods that are skipped by default, such as `__call__`, keep everything else by starting the list with `all`:

```md
[[autodoc]] Flock
    - all
    - __call__
```

> [!TIP]
> `[[autodoc]]` works on any page. Keeping it to the Reference section makes cross-references predictable, though, because each object then has exactly one home.

## Cross-references

Inside pages and docstrings, put an object's name in backticks inside brackets to link to its documentation:

| You write | It renders as |
|---|---|
| `` [`Flock`] `` | a link to `Flock`, shown as `Flock` |
| `` [`Flock.run`] `` | a link to the method, shown as `Flock.run` |
| `` [`utils.load_config`] `` | shown with its path, `utils.load_config` |
| `` [`~utils.load_config`] `` | shown without its path, `load_config` |

The object must be documented with `[[autodoc]]` somewhere in the same docs, which is how the link knows its target page.

## Building without heavy dependencies

The package is imported to read its docstrings. If it imports something heavy at module level (for example `torch`), mock it instead of installing it:

```bash
doc-builder build flock docs/source --mock_deps torch,triton --html
```

Mocked modules import cleanly, can be subclassed and used as decorators, and show up in signatures under their real names. A package that is actually installed is never mocked. In CI, pass the same list as the `mock_deps` input of [`build_docs.yml`](workflows#build-docs).

## Docs without a package

If the docs don't belong to an importable package, or you just haven't set up autodoc yet, pass `--not_python_module` (`not_python_module: true` in CI). Autodoc and `objects.inv` are skipped. These docs are built that way.
