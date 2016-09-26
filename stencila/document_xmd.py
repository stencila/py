import re
import copy

from lxml import etree as xml

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
        Load a document from a XMarkdown string

        Conversion from Markdown to internal HTML is done via Pandoc with
        pre and post processing steps
        """
        lang = format[:-2]
        md = self.load_pre(xmd, lang)
        doc.html = pandoc.convert(md, 'md', 'html')
        self.load_post(doc, lang)

    def load_pre(self, xmd, lang):
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
        line_re = re.compile(r'^```\s*{(' + lang + r')(\s+[^}]+?)?}\s*$')
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

    def load_post(self, doc, lang):
        """
        Postprocessing of a document after it has been loaded from Pandoc HTML.

        Converts ``<pre><code>`` and ``<code>`` elements to the equivalent
        Stencila Document directives:

        * ``<pre class="r"><code>...`` to ``<pre data-execute="r">...``
        * ``<code>r x</code>`` to ``<span data-print="r x"></span>``
        """
        for elem in doc.select('pre[class^=' + lang + ']'):
            id = elem.get('id')
            args = [lang]
            for name, value in elem.items():
                if name == 'fig.width':
                    args.append('width %s' % value)
                elif name == 'fig.height':
                    args.append('height %s' % value)
                elem.attrib.pop(name)
            code = elem.cssselect('code')[0].text

            elem.clear()

            if id:
                elem.set('id', id)
            elem.set('data-execute', ' '.join(args))
            elem.text = code

        for elem in doc.select('code'):
            if elem.text[:(len(lang)+1)] == lang + ' ':
                elem.tag = 'span'
                elem.set('data-print', elem.text[(len(lang)+1):])
                elem.text = ''
        return doc

    def dump(self, doc, format):
        """
        Dump a document to a XMarkdown string

        Conversion from internal HTML to Markdown is done via Pandoc with
        pre and post processing steps
        """
        lang = format[:-2]
        html = self.dump_pre(doc, lang)
        xmd = pandoc.convert(html, 'html', 'md')
        return self.dump_post(xmd, lang)

    def dump_pre(self, doc, lang):
        """
        Generate HTML for Pandoc to convert to Markdown

        Converts execute and print directives to Pandoc equivalents:

        * ``<pre id="label" data-execute="r height 6">..`` to ``<pre class="r" id="label" fig.height="6"><code>...``
        * ``<span data-print="r x"></span>`` to ``<code>r x</code>``

        For RMarkdown, arguments of execute directives are translated to Knitr chunk option equivalents.
        For other formats
        """
        clone = copy.deepcopy(doc)

        for elem in clone.select('[data-execute]'):
            id = elem.get('id')
            args = elem.get('data-execute').split()
            code = elem.text

            elem.clear()
            elem.tag = 'pre'
            if id:
                elem.set('id', id)
            elem.set('class', lang)
            for index in range(1, len(args), 2):
                name = args[index]
                value = args[index + 1]
                if lang == 'r':
                    name = {
                        'width': 'fig.width',
                        'height': 'fig.height'
                    }.get(name, name)
                elem.set(name, value)
            code_elem = xml.Element('code')
            code_elem.text = code
            elem.append(code_elem)

        for elem in clone.select('[data-print]'):
            args = elem.get('data-print')
            elem.clear()
            elem.tag = 'code'
            elem.text = lang + ' ' + args

        return clone.dump('html', pretty=False)

    def dump_post(self, md, lang):
        """
        Postprocess Markdown generated by Pandoc to convert it to XMarkdown
        """
        xmd = ''
        line_re = re.compile(r'^```\s*{(#([\w\-\.]+)\s+)?\.(' + lang + r')(\s+[^}]+?)?}\s*$')
        attr_re = re.compile(r'([^\s=]+)\s*=\s*(.+)')
        for line in md.splitlines():
            match = line_re.match(line)
            if match:
                xmd += '``` {' + match.group(3)
                label = match.group(2)
                if label:
                    xmd += ' ' + label
                attrs = match.group(4)
                if attrs:
                    options = []
                    for attr in attrs.split():
                        attr = attr.strip()
                        match = attr_re.match(attr)
                        if match:
                            name, value = match.groups()
                            assert value[0] == '"' and value[len(value)-1] == '"'
                            value = value[1:-1]
                            options.append('%s=%s' % (name, value))
                        else:
                            raise RuntimeError('Unmatched attribute:\n  attr: ' + attr)
                    xmd += ', ' + ', '.join(options)
                xmd += '}\n'
            else:
                xmd += line + '\n'
        return xmd
