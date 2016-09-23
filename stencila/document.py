import os

from .component import Component
from .helpers.pandoc import pandoc


class Document(Component):

    def __init__(self, address=None, path=None):
        self._content = ''

        Component.__init__(self, address, path)

    def content(self, value=None, format='html'):
        if not value:
            if format == 'html':
                return self._content
            else:
                return pandoc.convert(self._content, 'html', format).strip()
        else:
            if format == 'html':
                self._content = value
            else:
                self._content = pandoc.convert(value, format, 'html').strip()

    @property
    def html(self):
        return self._content

    @html.setter
    def html(self, html):
        self._content = html

    @property
    def md(self):
        return self.content(format='md')

    @md.setter
    def md(self, md):
        self.content(md, format='md')

    @classmethod
    def know(clazz, path):
        root, ext = os.path.splitext(path)
        if ext in ['.html', '.md', '.odt', '.docx']:
            return True
        return False

    def read(self, path='', format=None):
        path = Component.read(self, path)
        if format is None:
            root, ext = os.path.splitext(path)
            if len(ext) > 1:
                format = ext[1:]

        if format == 'html':
            with open(path) as file:
                self._content = file.read().strip()
        elif format in ('md', 'odt', 'docx'):
            self._content = pandoc.read(path, format, 'html').strip()
        else:
            raise RuntimeError('Unhandled format\n  format: %s' % format)

        return self

    def write(self, path='', format=None):
        path = Component.write(self, path)
        if format is None:
            root, ext = os.path.splitext(path)
            if len(ext) > 1:
                format = ext[1:]

        if format == 'html':
            with open(path, 'w') as file:
                content = self._content
                if content[-1:] != '\n':
                    content += '\n'
                file.write(content)
        elif format in ('md', 'odt', 'docx'):
            pandoc.write(self._content, path, 'html', format)
        else:
            raise RuntimeError('Unhandled format\n  format: %s' % format)

        return self
