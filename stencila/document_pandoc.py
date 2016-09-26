from lxml import etree as xml

from .component_converter import ComponentConverter
from .helpers.pandoc import pandoc


class DocumentPandoc(ComponentConverter):
    """
    A default Document converter which uses Pandoc

    This converter is used for conversion of formats that do not need any pre or post processing
    before/after Pandoc conversion.
    """

    def load(self, doc, content, format):
        doc.html = pandoc.convert(content, format, 'html')

    def dump(self, doc, format):
        return pandoc.convert(doc.html, 'html', format).strip()

    def read(self, doc, path, format):
        doc.html = pandoc.read(path, format, 'html')

    def write(self, doc, path, format):
        pandoc.write(doc.html, path, 'html', format)
