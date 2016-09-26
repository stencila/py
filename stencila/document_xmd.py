import re

from .component_converter import ComponentConverter
from .helpers.pandoc import pandoc


class DocumentXmd(ComponentConverter):
    """
    A Document converter for XMarkdown.

    XMarkdown is our name for RMarkdown-like formats, that is, RMarkdown but extended to language
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

    def load(self, doc, xmd, format):
        """
        Load a document from XMarkdown

        Conversion from Markdown to internal HTML is done via Pandoc with
        pre and post processing steps
        """
        lang = format[:-2]
        md = self.load_pre(xmd, lang)
        doc.html = pandoc.convert(md, 'md', 'html')
        self.load_post(doc, lang)
        return doc

    def load_pre(self, xmd, lang=None):
        """
        Preprocessing of XMarkdown to Pandoc compatible Markdown

        The RMarkdown (and thus XMarkdown) format for block code chunks is not equivalent to Pandoc's format
        for fenced code block attributes (http://pandoc.org/MANUAL.html#extension-fenced_code_attributes).
        This method transforms code chunk string to what Pandoc expects:

        * the chunk language is converted to a class (e.g. ``.r``)
        * the chunk label is converted to an id (e.g. ``#my-chunk``)
        * chunk options are converted into an attribute (e.g. ``fig.height="6"``)
        """
        md = ''
        line_re = re.compile(r'^```\s*{(' + lang + ')\s*([^}]+?)?}\s*$')
        option_re = re.compile(r'([^\s=]+)\s*=\s*(.+)')
        for line in xmd.splitlines():
            match = line_re.match(line)
            if match:
                md += '``` {.' + match.group(1)
                options = match.group(2)
                if options:
                    id = None
                    attrs = []
                    for option in options.split(','):
                        option = option.strip()
                        match = option_re.match(option)
                        if match:
                            name, value = match.groups()
                            value = value.replace('"', '\"')
                            attrs.append('%s="%s"' % (name, value))
                        else:
                            if id is None:
                                id = option
                            else:
                                raise RuntimeError('Attempting to set chunk label again?\n  option: ' + option)
                    if id:
                        md += ' #%s' % id
                    if len(attrs):
                        md += ' ' + ' '.join(attrs)

                md += '}\n'
            else:
                md += line + '\n'
        return md

    def load_post(self, doc, lang=None):
        """
        Prostprocessing of a document after it has been loaded from Pandoc HTML.

        Converts ``<pre><code>`` and ``<code>`` elements to the equivalent
        Stencila Document directives:

        * ``<pre class="r"><code>...`` to ``<pre data-execute="r">...``
        * ``<code>r x</code>`` to ``<span data-print="r x"></span>``
        """
        for elem in doc.select('pre[class^=' + lang + ']'):
            id = elem.get('id')
            options = [lang]
            for name, value in elem.items():
                if name == 'fig.width':
                    options.append('width %s' % value)
                elif name == 'fig.height':
                    options.append('height %s' % value)
                elem.attrib.pop(name)
            code = elem.cssselect('code')[0].text

            elem.clear()

            if id:
                elem.set('id', id)
            elem.set('data-execute', ' '.join(options))
            elem.text = code

        for elem in doc.select('code'):
            if elem.text[:(len(lang)+1)] == lang + ' ':
                elem.tag = 'span'
                elem.set('data-print', elem.text)
                elem.text = ''
        return doc

    def dump(self, doc):
        """
        Dump a document to XMarkdown

        Conversion from internal HTML to Markdown is done via Pandoc with
        pre and post processing steps
        """
        self.dump_post(pandoc.convert(self.dump_pre(html), 'html', 'md'))

    def dump_pre(doc, lang):
        """
        Create a copy of a document that has been transformed
        to Pandoc compatible HTML

        Converts execute and print directives to Pandoc equivalents:

        * ``<pre id="label" data-execute="r height 6">..`` to ``<pre class="r" id="label" fig.height="6"><code>...``
        * ``<span data-print="r x"></span>`` to ``<code>r x</code>``
        """
        clone = copy.deepcopy(doc)

        for elem in clone.select('[data-execute]'):
            options = elem.get('data-execute')
            elem.attrib.clear()
            elem.set('class', lang)

        for elem in clone.select('[data-print]'):
            expr = elem.get('data-print')
            elem.clear()
            elem.tag = 'code'
            elem.text = lang + ' ' + expr

        return clone.dump('html')


    def dump_post(md, lang):
        """
        Remove the ext
        """
        xmd = ''
        line_re = re.compile(r'^```\s*{\.(' + lang + '\s*([^}]+?)?)}\s*$')
        for line in md.splitlines():
            match = line_re.match(line)
            if match:
                xmd += '``` {' + match.group(1) + '}\n'
            else:
                xmd += line + '\n'
        return xmd
