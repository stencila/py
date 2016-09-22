import os

from .component import Component
from .helpers.pandoc import pandoc


class Document(Component):

    @staticmethod
    def open(address, path):
        root, ext = os.path.splitext(path)
        if ext in ['.html', '.md']:
            return Document(address, path)
        return None

    def __init__(self, address=None, path=None):
        self.__content = ''

        Component.__init__(self, address, path)

    def read(self, path='', format=None):
        path = Component.read(self, path)

        if format is None:
            root, ext = os.path.splitext(path)
            if len(ext) > 1:
                format = ext[1:]

        if format == 'html':
            with open(path) as file:
                self.__content = file.read()
        elif format == 'md':
            self.__content = pandoc(path, '--from', 'markdown+pipe_tables')

        return self

    def write(self, path=''):
        path = Component.write(self, path)

        return self

    def content(self, format='html'):
        if format == 'html':
            return self.__content
        else:
            raise RuntimeError('Unhandled format\n  format: %s' % format)
