import os

from lxml import etree as xml

from .component import Component
from .utilities import path_to_format
from .document_html import DocumentHtml
from .document_xmd import DocumentXmd
from .document_xtex import DocumentXtex
from .document_pandoc import DocumentPandoc


class Document(Component):

    def __init__(self, address=None, path=None):
        self._content = xml.Element('root')

        Component.__init__(self, address, path)

    @property
    def html(self):
        return self.dump(format='html')

    @html.setter
    def html(self, content):
        self.load(content, format='html')

    @property
    def md(self):
        return self.dump(format='md')

    @md.setter
    def md(self, content):
        self.load(content, format='md')

    @property
    def rmd(self):
        return self.dump(format='rmd')

    @rmd.setter
    def rmd(self, content):
        self.load(content, format='rmd')

    @staticmethod
    def converter(format):
        """
        Get the Document converter for a given format
        """
        if format == 'html':
            return DocumentHtml()
        elif format in ('xmd', 'jsmd', 'pymd', 'rmd'):
            return DocumentXmd()
        elif format in ('xtex', 'jstex', 'pytex', 'rtex', 'rnw'):
            return DocumentXtex()
        elif format in ('docx', 'md', 'odt'):
            return DocumentPandoc()
        else:
            raise RuntimeError('Unhandled format\n  format: %s' % format)

    @staticmethod
    def know(path):
        root, ext = os.path.splitext(path)
        format = path_to_format(path)
        try:
            Document.converter(format)
        except RuntimeError:
            return False
        else:
            return True

    def load(self, content, format='html', **options):
        self.converter(format).load(self, content, format, **options)
        return self

    def dump(self, format='html', **options):
        return self.converter(format).dump(self, format, **options)

    def read(self, path='', format=None):
        path = Component.read(self, path)
        if format is None:
            format = path_to_format(path)
        self.converter(format).read(self, path, format)
        return self

    def write(self, path='', format=None):
        path = Component.write(self, path)
        if format is None:
            format = path_to_format(path)
        self.converter(format).write(self, path, format)
        return self

    def select(self, selector, type='css'):
        if type == 'css':
            return self._content.cssselect(selector)
        else:
            return self._content.xpath(selector)
