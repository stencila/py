from lxml import etree as xml

from .component_converter import ComponentConverter


class DocumentHtml(ComponentConverter):
    """
    A Document converter for HTML.

    The internal, in-memory representation of Stencila Documents is a XML tree.
    So this converter simply converts that tree from/to a HTML string or file
    """

    def load(self, doc, html, format, **options):
        doc._content = xml.fromstring('<root>' + html + '</root>')

    def dump(self, doc, format, pretty=True):
        if pretty:
            html = doc._content.text if doc._content.text else ''
            html += ''.join([xml.tostring(child, pretty_print=True) for child in doc._content])
            return html.strip()
        else:
            return xml.tostring(doc._content).strip()[6:-7]  # Remove start and end `<root>` tags
