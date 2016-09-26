import copy
import os
import re

from lxml import etree as xml

from .component import Component
from .utilities import path_to_format
from .document_html import DocumentHtml
from .document_xmd import DocumentXmd
from .document_xtex import DocumentXtex


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
        return self.converter(format).load(self, content, format, **options)

    def dump(self, format='html', **options):
        return self.converter(format).dump(self, format, **options)

    def read(self, path='', format=None):
        path = Component.read(self, path)
        if format is None:
            format = path_to_format(path)
        return self.converter(format).read(path)

    def write(self, path='', format=None):
        path = Component.write(self, path)
        if format is None:
            format = path_to_format(path)
        return self.converter(format).write(path)

    def select(self, selector, type='css'):
        if type == 'css':
            return self._content.cssselect(selector)
        else:
            return self._content.xpath(selector)
