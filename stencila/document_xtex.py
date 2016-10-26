from .component_converter import ComponentConverter


class DocumentXtex(ComponentConverter):
    """
    A Document converter for XTex.

    XTex is our name for R's Sweave-like formats, that is, RMarkdown but extended to language
    X, where X includes Python, Javascript, etc.

    In RMarkdown, R code is embedded in "code chunks". There are two types of code chunks: inline and block.
    In XMarkdown, we allow both inline and block chunks to be defined in various languages using
    our usual language labels e.g. ``r``, ``py``, ``js``.

    Inline code chunks, equivalent to Stencila's print directive, are declared using Markdown code spans
    prefixed by the language label e.g.

        The answer is `r x`

    Block code chunks, equivalent to Stencila's execute directive, are declared using Markdown fenced code blocks
    with attributes prefixed by the language label and, optionally, a chunk label and other options e.g.

        ```{r myplot, fig.width=6, fig.height=7}
        plot(x,y)
        ```

    Here ``myplot`` is the chunk label and ```fig.width=6, fig.height=7``` are chunk options.
    A list of chunk options, recognised by the RMarkdown renders, Knitr,
    is available at http://yihui.name/knitr/options/. Not all of these will be relevant or supported in Stencila.
    """