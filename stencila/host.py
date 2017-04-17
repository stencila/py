import argparse
import os
import platform
import random
import string
import subprocess

from .version import __version__
from .python_context import PythonContext
from .host_http_server import HostHttpServer

TYPES = {
    'PythonContext': PythonContext
}


class HostConfig(dict):

    def __init__(self, instance):
        # Defaults
        self['startup'] = {
            'serve': False,
            'discover': False
        }

        # User config file overrides
        user = os.path.join(os.path.expanduser('~'), '.stencila', '.config.yaml')
        if os.path.exists(user):
            update(self, yaml.read(user))

        # Local config file overrides
        local = os.path.join('.', '.config.yaml')
        if os.path.exists(local):
            update(self, yaml.read(local))

        # Environment overrides
        env = os.environ
        if env.get('STENCILA_STARTUP_SERVE'):
            self['startup']['serve'] = env.get('STENCILA_STARTUP_SERVE') in ('true', '1')

        # Command line argument overrides
        parser = argparse.ArgumentParser()
        parser.add_argument('--startup-serve', default=None)
        args, unknown = parser.parse_known_args()
        if args.startup_serve:
            self['startup']['serve'] = args.startup_serve in ('true', '1')


class Host(object):
    """
    A `Host` allows you to create, get, run methods of, and delete instances of various types.
    The types can be thought of a "services" provided by the host e.g. `NoteContext`, `FilesystemStorer`

    The API of a host is similar to that of a HTTP server. It's methods names
    (e.g. `post`, `get`) are similar to HTTP methods (e.g. `POST`, `GET`) but
    the sematics sometimes differ (e.g. a host's `put()` method is used to call an
    instance method)

    A `Host` is not limited to beng served by HTTP and it's methods are exposed by both `HostHttpServer`
    and `HostWebsocketServer`. Those other classes are responsible for tasks associated with
    their communication protocol (e.g. serialising and deserialising objects).

    This is a singleton class. There should only ever be one `Host`
    in memory in each process (although, for purposes of testing, this is not enforced)
    """

    def __init__(self):
        self._home = os.path.join(os.path.expanduser('~'), '.stencila')
        self._servers = {}
        self._instances = {}

    def options(self):
        """
        Get a manifest for this host

        The manifest describes the host and it's capabilities. It is used
        by peer hosts to determine which "types" this host provides and
        which "instances" have already been instantiated.

        :returns: A manifest object
        """
        return {
            'stencila': {
                'package': 'py',
                'version': __version__
            },
            'urls': self.urls,
            'types': list(TYPES.keys()),
            'instances': list(self._instances.keys())
        }

    def post(self, type):
        """
        Create a new instance of a type

        :param type: Type of instance
        :returns: ID string of newly created instance
        """
        Class = TYPES.get(type)
        if Class:
            instance = Class()
            id = ''.join(random.choice(string.ascii_lowercase + string.digits) for char in range(12))
            self._instances[id] = instance
            return id
        else:
            raise Exception('Unknown type: %s' % type)

    def get(self, id):
        """
        Get an instance

        :param id: ID of instance
        :returns: The instance
        """
        instance = self._instances.get(id)
        if instance:
            return instance
        else:
            raise Exception('Unknown instance: %s' % id)

    def put(self, id, method, kwargs={}):
        """
        Call a method of an instance

        :param id: ID of instance
        :param method: Name of instance method
        :param kwargs: An array of method arguments
        :returns: Result of method call
        """
        instance = self._instances.get(id)
        if instance:
            try:
                func = getattr(instance, method)
            except AttributeError:
                raise Exception('Unknown method: %s' % method)
            else:
                return func(**kwargs)
        else:
            raise Exception('Unknown instance: %s' % id)

    def delete(self, id):
        """
        Delete an instance

        :param id: ID of instance
        """
        if id in self._instances:
            del self._instances[id]
        else:
            raise Exception('Unknown instance: %s' % id)

    def start(self):
        """
        Start serving this host

        Currently, HTTP is the only server available
        for hosts. We plan to implement a `HostWebsocketServer` soon.

        :returns: self
        """
        if 'http' not in self._servers:
            server = HostHttpServer(self)
            self._servers['http'] = server
            server.start()
            print 'Host is served at: %s' % ', '.join(self.urls)
        return self

    def stop(self):
        """
        Stop serving this host

        :returns: self
        """
        server = self._servers.get('http')
        if server:
            server.stop()
            del self._servers['http']
        return self

    @property
    def servers(self):
        return self._servers.keys()

    @property
    def urls(self):
        return [server.url for server in self._servers.values()]

    def view(self):
        """
        View this host in the browser

        Opens the default browser at the URL of this host
        """
        self.start()
        url = self._servers['http'].url
        if platform.system() == 'Linux':
            subprocess.call('2>/dev/null 1>&2 xdg-open "%s"' % url, shell=True)
        else:
            subprocess.call('open "%s"' % url, shell=True)


host = Host()
