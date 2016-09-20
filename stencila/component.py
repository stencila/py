import errno
import os
import random
import string

from .main import components, resolve, obtain


class Component:

    def __init__(self, address=None):
        """
        Create a component

        :param address: The address of the component
        """
        if address:
            self.__address = resolve(address)
            try:
                self.__path = obtain(self.__address)
            except IOError, exc:
                if self.__address[:7] == 'file://':
                    self.__path = self.__address[7:]
                    return
                else:
                    raise exc
            self.read()
        else:
            self.__address = 'mem://' + ''.join([random.choice(string.ascii_lowercase+string.digits) for i in range(12)])
            self.__path = None

        components.append(self)

    def __del__(self):
        if components:
            components.pop(components.index(self))

    def address(self):
        return self.__address

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

    def page(self, main=''):
        return '''
        <!DOCTYPE html>
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <link rel="stylesheet" type="text/css" href="/web/%(type)s.min.css">
                <script src="/web/%(type)s.min.js"></script>
            </head>
            <body>
                <main id="main">%(main)s</main>
            </body>
        </html>''' % {
            'type': self.__class__.__name__.lower(),
            'main': main
        }
