import itertools

from lxml import etree as xml

from .component_converter import ComponentConverter


class DocumentHtml(ComponentConverter):
    """
    A Document converter for HTML.

    The internal, in-memory representation of Stencila Documents is a XML tree.
    So this converter simply converts that tree from/to a HTML string or file
    """

    def load(self, doc, html, format='html', **options):
        """
        Load a document from a HTML string
        """
        doc._content = xml.fromstring('<root>' + html + '</root>')

    def dump(self, doc, format='html', pretty=True):
        """
        Dump a document to a HTML string
        """
        if pretty:
            indented = xml.tostring(doc._content, encoding='unicode', pretty_print=True).strip()[6:-7]
            inner = ''
            for line in indented.splitlines():
                inner += (line[2:] if line[:2] == '  ' else line) + '\n'
            return inner.strip()
        else:
            return xml.tostring(doc._content, encoding='unicode').strip()[6:-7]  # Remove start and end `<root>` tags
