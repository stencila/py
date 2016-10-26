import errno
import os
import random
import string

import requests

from .version import __version__
from . import instance_
from .component_html import ComponentHtml
from .component_json import ComponentJson
from .component_meta_html import ComponentMetaHtml


class Component(object):

    def __init__(self, address=None, path=None):
        """
        Create a component

        :param address: The address of the component
        """
        from .instance_ import instance
        if address:
            self._address = instance.lengthen(address)
            if path:
                self._path = path
            else:
                self._path = instance.clone(self._address)
            self.read()
        else:
            self._address = 'mem://' + ''.join(
                [random.choice(string.ascii_lowercase+string.digits) for i in range(12)]
            )
            self._path = None

        self._id = os.urandom(32).encode('hex')

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

    # Accessors for compatability with remote objects

    def get(self, name):
        return getattr(self, name)

    def set(self, name, value):
        setattr(self, name, value)
        return self

    def call(self, name, *args, **kwargs):
        return getattr(self, name)(*args, **kwargs)

    # Descriptors

    @property
    def type(self):
        return self.__class__.__name__.lower()

    @property
    def id(self):
        return self._id

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

    @property
    def path(self):
        return self._path

    @staticmethod
    def extension(path=None):
        root, ext = os.path.splitext(path)
        return ext[1:].lower()

    @staticmethod
    def converter(format):
        """
        Get the converter for a given format
        """
        if format == 'html':
            return ComponentHtml()
        elif format == 'json':
            return ComponentJson()
        else:
            raise RuntimeError('Unhandled format\n  format: %s' % format)

    @staticmethod
    def know(path):
        """
        Does this component know how to handle this path?

        This method is mostly used internally to determine which
        class of ``Component`` should open a path. It should be
        overidden in derived classes
        """
        return 'no'

    @classmethod
    def open(cls, address, path):
        know = cls.know(path)
        if know == 'yes':
            return cls(address, path)
        return None

    def load(self, content, format='html', **options):
        self.converter(format).load(self, content, format, **options)
        return self

    def dump(self, format='html', **options):
        return self.converter(format).dump(self, format, **options)

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

    def show(self, format='html'):
        if format == 'html':
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
                'content': self.dump('html')
            }
        else:
            return self.dump('json')

    @property
    def url(self):
        from .instance_ import instance
        return instance.url(self)

    def view(self):
        from .instance_ import instance
        return instance.view(self)


class RemoteComponent(object):
    """
    To provide a consistent API across host languages
    we provide three methods

    * ``component.get(name)``
    * ``component.set(name, value)``
    * ``component.call(name, **kwargs)``

    But because Python allows operater overloading these can be accessed using

    * ``component.name``
    * ``component.name = value``
    * ``component.call(arg=value)``

    Currently uses HTTP requests but could allow for Websocket or other protocol.

    TODO better serialization. perhaps with a type name in a header - i.e. pass plain json 
    but header can specify type so the deserialization can work on Tables etc
    """

    properties = [
        'type', 'address'
    ]
    methods = []

    def __init__(self, host, address):
        self.__dict__['_host'] = host
        self.__dict__['_address'] = address

    def get(self, name):
        if name in self.properties:
            url = '%s/%s!%s' % (self._host, self._address, name)
            response = requests.get(url)
            return response.json() #TODO smart deserialisation in native type or component
        elif name in self.methods:
            return RemoteComponentMethod(self, name)
        else:
            raise RuntimeError('No such property')

    def set(self, name, value):
        if name in self.properties:
            url = '%s/%s!%s' % (self._host, self._address, name)
            response = requests.put(url, json=value)
            return self
        elif name in self.methods:
            raise RuntimeError('Attempting to set a method (can only call)')
        else:
            raise RuntimeError('No such property')

    def call(self, name, *args, **kwargs):
        return RemoteComponentMethod(self, name)(*args, **kwargs)

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        return self.set(name, value)


class RemoteComponentMethod(object):

    def __init__(self, remote, name):
        self._remote = remote
        self._name = name

    def __call__(self, *args, **kwargs):
        remote = self._remote
        name = self._name
        if name in remote.methods:
            url = '%s/%s!%s' % (remote._host, remote._address, name)
            print 'trying to set property', url
            response = requests.post(url, json=kwargs) # TODO meld args and kwargs
            return response.json()
        elif name in remote.properties:
            raise RuntimeError('Attempting to call a property (can only get or set)')
        else:
            raise RuntimeError('No such property')
