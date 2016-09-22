import errno
import os
import random
import string

from .version import __version__
from . import session_instance


class Component:

    def __init__(self, address=None, path=None):
        """
        Create a component

        :param address: The address of the component
        """
        from .session_instance import instance as session
        if address:
            self._address = session.resolve(address)
            if path:
                self._path = path
            else:
                self._path = session.obtain(self._address)
            self.read()
        else:
            self._address = 'mem://' + ''.join(
                [random.choice(string.ascii_lowercase+string.digits) for i in range(12)]
            )
            self._path = None

        session.register(self)

    def __del__(self):
        # On final garbage collection, the session may not
        # exists, so deal with that
        try:
            from .session_instance import instance as session
        except ValueError:
            pass
        else:
            session.deregister(self)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.address)

    @property
    def type(self):
        return self.__class__.__name__.lower()

    @property
    def address(self):
        return self._address

    @property
    def title(self):
        return 'Untitled'

    @property
    def summary(self):
        return ''

    @property
    def keywords(self):
        return []

    def content(self, format='html'):
        return ''

    @property
    def path(self):
        return self._path

    def read(self, path=''):
        if path is None or path == '':
            path = self._path

        if not os.path.exists(path):
            raise IOError('Filesystem path does not exist\n  path: %s' % path)

        self._path = path

        return path

    def write(self, path=''):
        if path is None or path == '':
            path = self._path

        root, ext = os.path.splitext(path)
        dir = path if ext == '' else os.path.dirname(path)
        if not os.path.exists(dir):
            try:
                os.makedirs(dir)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

        self._path = path

        return path

    def page(self):
        return '''<!DOCTYPE html>
<html>
    <head>
        <title>%(title)s</title>
        <meta name="address" content="%(address)s">
        <meta name="description" content="%(summary)s">
        <meta name="keywords" content="%(keywords)s">
        <meta name="generator" content="stencila-%(package)s-%(version)s">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="/web/%(type)s.min.css">
    </head>
    <body>
        <main id="content">%(content)s</main>
        <script src="/web/%(type)s.min.js"></script>
    </body>
</html>''' % {
            'title': self.title,
            'address': self.address,
            'summary': self.summary,
            'keywords': ', '.join(self.keywords),
            'package': 'py',
            'version': __version__,
            'type': self.type,
            'content': self.content()
        }

    def view(self):
        from .session_instance import instance as session
        return session.view(self)
