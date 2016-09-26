import errno
import os
import random
import string

from .version import __version__
from . import instance_
from .component_meta_html import ComponentMetaHtml
from .component_meta_yaml import ComponentMetaYaml


class Component(object):

    def __init__(self, address=None, path=None):
        """
        Create a component

        :param address: The address of the component
        """
        from .instance_ import instance
        if address:
            self._address = instance.resolve(address)
            if path:
                self._path = path
            else:
                self._path = instance.obtain(self._address)
            self.read()
        else:
            self._address = 'mem://' + ''.join(
                [random.choice(string.ascii_lowercase+string.digits) for i in range(12)]
            )
            self._path = None

        self._meta = {}

        instance.register(self)

    def __del__(self):
        # On final garbage collection, the instance may not
        # exists, so deal with that
        try:
            from .instance_ import instance
        except ValueError:
            pass
        else:
            instance.deregister(self)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.address)

    # Descriptors

    @property
    def type(self):
        return self.__class__.__name__.lower()

    @property
    def address(self):
        return self._address

    @property
    def title(self):
        return self._meta.get('title')

    @title.setter
    def title(self, value):
        self._meta['title'] = value

    @property
    def description(self):
        return self._meta.get('description')

    @description.setter
    def description(self, value):
        self._meta['description'] = value

    @property
    def summary(self):
        return self._meta.get('summary')

    @summary.setter
    def summary(self, value):
        self._meta['summary'] = value

    @property
    def keywords(self):
        return self._meta.get('keywords')

    @keywords.setter
    def keywords(self, value):
        self._meta['keywords'] = value

    @property
    def authors(self):
        return self._meta.get('authors')

    @authors.setter
    def authors(self, value):
        self._meta['authors'] = value

    @property
    def date(self):
        return self._meta.get('date')

    @date.setter
    def date(self, value):
        self._meta['date'] = value

    def content(self, format='html'):
        return ''

    @property
    def path(self):
        return self._path

    def know(self, path):
        """
        Does this component know how to handle this path?

        This method is mostly used internally to determine which
        class of ``Component`` should open a path. It should be
        overidden in derived classes
        """
        return False

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

    def get(self, format='html'):
        assert format == 'html'

        return '''<!DOCTYPE html>
<html>
    <head>
        %(meta)s
        <meta name="generator" content="stencila-%(package)s-%(version)s">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="/web/%(type)s.min.css">
    </head>
    <body>
        <main id="content">%(content)s</main>
        <script src="/web/%(type)s.min.js"></script>
    </body>
</html>''' % {
            'meta': ComponentMetaHtml().dump(self),
            'package': 'py',
            'version': __version__,
            'type': self.type,
            'content': self.content()
        }

    @property
    def url(self):
        from .instance_ import instance
        return instance.url(self)

    def view(self):
        from .instance_ import instance
        return instance.view(self)
