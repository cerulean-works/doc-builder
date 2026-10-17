# Docstring format

`[[autodoc]]` reads Google-style docstrings written in Markdown, not reStructuredText. Everything in [Markdown syntax](syntax) works inside docstrings too, including `` [`Object`] `` cross-references.

Put code, argument names, `True`, `None` and string values in backticks. Examples use [doctest](https://docs.python.org/3/library/doctest.html) syntax, so they can be tested.

## Description

For a class or function description string, use Markdown with [all of doc-builder's syntax](syntax).

## Arguments

Arguments of a function/class/method should be defined with the `Args:` (or `Arguments:` or `Parameters:`) prefix, followed by a line return and
an indentation. The argument should be followed by its type, with its shape if it is a tensor, a colon, and its
description:

```
    Args:
        n_layers (`int`): The number of layers of the model.
```

If the description is too long to fit in one line, another indentation is necessary before writing the description
after the argument.

```
    Args:
        input_ids (`torch.LongTensor` of shape `(batch_size, sequence_length)`):
            Indices of input sequence tokens in the vocabulary.

            Indices can be obtained using [`AlbertTokenizer`]. See [`~PreTrainedTokenizer.encode`] and
            [`~PreTrainedTokenizer.__call__`] for details.

            [What are input IDs?](../glossary#input-ids)
```

## Attributes

If a class is similar to that of a dataclass but the parameters do not align to the available attributes of the class, such as in the below example, `Attributes` instance should be rewritten as `**Attributes**` in order to have the documentation properly render these. Otherwise it will assume that `Attributes` is synonymous to `Parameters`.

```diff
  class SomeClass:
      """
      Docstring
-     Attributes:
+     **Attributes**:
          - **attr_a** (`type_a`) -- Doc a
          - **attr_b** (`type_b`) -- Doc b
      """
      def __init__(self, param_a, param_b):
          ...
```

## Parameter typing and default value

For optional arguments or arguments with defaults we follow the following syntax. Imagine we have a function with the
following signature:

```
def my_function(x: str = None, a: float = 1):
```

then its documentation should look like this:

```
    Args:
        x (`str`, *optional*):
            This argument controls ...
        a (`float`, *optional*, defaults to 1):
            This argument is used to ...
```

Note that we always omit the "defaults to \`None\`" when None is the default for any argument. Also note that even
if the first line describing your argument type and its default gets long, you can't break it on several lines. You can
however write as many lines as you want in the indented description (see the example above with `input_ids`).

If your argument has for type a class defined in the package, you can use the syntax we saw earlier to link to its
documentation:

```
    Args:
         config ([`BertConfig`]):
            Model configuration class with all the parameters of the model.

            Initializing with a config file does not load the weights associated with the model, only the
            configuration. Check out the [`~PreTrainedModel.from_pretrained`] method to load the model weights.
```

## Returns

The return block should be introduced with the `Returns:` prefix, followed by a line return and an indentation.
The first line should be the type of the return, followed by a line return. No need to indent further for the elements
building the return.

Here's an example for a single value return:

```
    Returns:
        `List[int]`: A list of integers in the range [0, 1] --- 1 for a special token, 0 for a sequence token.
```

Here's an example for tuple return, comprising several objects:

```
    Returns:
        `tuple(torch.FloatTensor)` comprising various elements depending on the configuration ([`BertConfig`]) and inputs:
        - ** loss** (*optional*, returned when `masked_lm_labels` is provided) `torch.FloatTensor` of shape `(1,)` --
          Total loss as the sum of the masked language modeling loss and the next sequence prediction (classification) loss.
        - **prediction_scores** (`torch.FloatTensor` of shape `(batch_size, sequence_length, config.vocab_size)`) --
          Prediction scores of the language modeling head (scores for each vocabulary token before SoftMax).
```

## Yields

Similarly, `Yields` is also supported.

```
Yields:
    `tuple[str, io.BufferedReader]`:
        2-tuple (path_within_archive, file_object).
        File object is opened in binary mode.
```

## Raises

You can also document `Raises`.

```
    Args:
         config ([`BertConfig`]):
            Model configuration class with all the parameters of the model.

            Initializing with a config file does not load the weights associated with the model, only the
            configuration. Check out the [`~PreTrainedModel.from_pretrained`] method to load the model weights.

    Raises:
        `pa.ArrowInvalidError`: if the arrow data casting fails
        TypeError: if the target type is not supported according, e.g.
            - point1
            - point2
        [`HTTPError`](https://2.python-requests.org/en/master/api/#requests.HTTPError) if credentials are invalid
        [`HTTPError`](https://2.python-requests.org/en/master/api/#requests.HTTPError) if connection got lost

    Returns:
        `List[int]`: A list of integers in the range [0, 1] --- 1 for a special token, 0 for a sequence token.
```

## Directives for Added, Changed, Deprecated

There are directives for `Added`, `Changed`, & `Deprecated`.
```
    Args:
        cache_dir (`str`, *optional*): Directory to cache data.
        config_name (`str`, *optional*): Name of the dataset configuration.
            It affects the data generated on disk: different configurations will have their own subdirectories and
            versions.
            If not provided, the default configuration is used (if it exists).

            <Added version="2.3.0">

            `name` was renamed to `config_name`.

            </Added>
        name (`str`): Configuration name for the dataset.

            <Deprecated version="2.3.0">

            Use `config_name` instead.

            </Deprecated>
```

