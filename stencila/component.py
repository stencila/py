import os
import errno


class Component:

    def __init__(self, path=''):
        self.__path = path
        if os.path.exists(path):
            self.read(path)

        components.append(self)

    def __del__(self):
        if components:
            components.pop(components.index(self))

    def path(self):
        return self.__path

    def read(self, path=''):
        if path is None or path == '':
            path = self.__path

        if not os.path.exists(path):
            raise IOError('Filesystem path does not exist\n  path: %s' % path)

        self.__path = path

        return path

    def write(self, path=''):
        if path is None or path == '':
            path = self.__path

        root, ext = os.path.splitext(path)
        dir = path if ext == '' else os.path.dirname(path)
        if not os.path.exists(dir):
            try:
                os.makedirs(dir)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

        self.__path = path

        return path

components = []
