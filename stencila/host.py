import collections
import datetime
import json
import os
import platform
import random
import signal
import string
import subprocess
import sys
import tempfile
import time

from .version import __version__
from .python_context import PythonContext
# from .sqlite_context import SqliteContext
from .host_http_server import HostHttpServer

# Resource types available
TYPES = {
    'PythonContext': PythonContext,
    # Temporarily disable this SqliteContext which does not support new API
    # 'SqliteContext': SqliteContext
}
# Resource types specifications
TYPES_SPECS = {
    name: clas.spec for (name, clas) in TYPES.items()
}


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
        self._id = 'py-' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(64))
        self._servers = {}
        self._started = None
        self._heartbeat = None
        self._instances = {}

    @property
    def id(self):
        return self._id

    def user_dir(self):
        """
        Get the current user's Stencila data directory.

        This is the directory that Stencila configuration settings, such as the
        installed Stencila hosts, and document buffers get stored.
        """

        osn = platform.system().lower()
        if osn == 'darwin':
            return os.path.join(os.getenv("HOME"), 'Library', 'Application Support', 'Stencila')
        elif osn == 'linux':
            return os.path.join(os.getenv("HOME"), '.stencila')
        elif osn == 'windows':
            return os.path.join(os.getenv("APPDATA"), 'Stencila')
        else:
            return os.path.join(os.getenv("HOME"), 'stencila')

    def temp_dir(self):
        """
        Get the current Stencila temporary directory
        """
        return os.path.join(tempfile.gettempdir(), 'stencila')

    def manifest(self):
        """
        Get a manifest for this host

        The manifest describes the host and it's capabilities. It is used
        by peer hosts to determine which "types" this host provides and
        which "instances" have already been instantiated.

        :returns: A manifest object
        """
        od = collections.OrderedDict
        manifest = od([
            ('stencila', od([
                ('package', 'py'),
                ('version', __version__)
            ])),
            ('run', [sys.executable, '-c', 'import stencila; stencila.run(echo=True)']),
            ('types', TYPES_SPECS),
            # For compatability with 0.27 API
            ('schemes', {
                'new': TYPES_SPECS
            })
        ])
        if self._started:
            manifest.update([
                ('id', self._id),
                ('process', os.getpid()),
                ('servers', self.servers),
                ('instances', list(self._instances.keys())),
                # For compatability with 0.27 API
                ('urls', self.urls)
            ])

        return manifest

    def install(self):
        """
        Installation of a host involves creating a file `py.json` inside of
        the user's Stencila data (see `user_dir()`) directory which describes
        the capabilities of this host.
        """
        dir = os.path.join(self.user_dir(), 'hosts')
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(os.path.join(dir, 'py.json'), 'w') as file:
            file.write(json.dumps(self.manifest(), indent=True))

    def post(self, type, name=None, options={}):
        """
        Create a new instance of a type

        :param type: Type of instance
        :param name: Name of new instance
        :param options: Additional arguments to pass to constructor
        :returns: Address of newly created instance
        """
        Class = TYPES.get(type)
        if Class:
            instance = Class(**options)
            if not name:
                name = ''.join(random.choice(string.ascii_lowercase + string.digits) for char in range(12))
            address = 'name://' + name
            self._instances[address] = instance
            return address
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
        :param kwargs: A dictionary of method arguments
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

    def start(self, address='127.0.0.1', port=2000, authorization=True, quiet=False):
        """
        Start serving this host

        Currently, HTTP is the only server available
        for hosts. We plan to implement a `HostWebsocketServer` soon.

        :returns: self
        """
        if 'http' not in self._servers:
            # Start HTTP server
            server = HostHttpServer(self, address, port, authorization)
            self._servers['http'] = server
            server.start()

            # Record start times
            self._started = datetime.datetime.now()
            self._heartbeat = datetime.datetime.now()

            # Register as a running host by creating a run file
            dir = os.path.join(self.temp_dir(), 'hosts')
            if not os.path.exists(dir):
                os.makedirs(dir)
            with open(os.path.join(dir, self.id + '.json'), 'w', 0o600) as file:
                file.write(json.dumps(self.manifest(), indent=True))

            if not quiet:
                urls = [s.ticketed_url() for s in self._servers.values()]
                print('Host has started at: %s' % ', '.join(urls))

        return self

    def stop(self, quiet=False):
        """
        Stop serving this host

        :returns: self
        """
        server = self._servers.get('http')
        if server:
            server.stop()
            del self._servers['http']

        # Deregister as a running host
        path = os.path.join(self.temp_dir(), 'hosts', self.id + '.json')
        if os.path.exists(path):
            os.remove(path)

        if not quiet:
            print('Host has stopped')

        return self

    def run(self, address='127.0.0.1', port=2000, authorization=True, quiet=False, echo=False):
        """
        Start serving this host and wait for connections
        indefinitely
        """
        if echo:
            quiet = True
        self.start(address=address, port=port, authorization=authorization, quiet=quiet)

        if echo:
            print(json.dumps(self.manifest(), indent=True))
            sys.stdout.flush()

        if not quiet:
            print('Use Ctrl+C to stop')

        # Handle SIGINT if this process is killed somehow other than by
        # Ctrl+C (e.g. by a parent peer)
        def stop(signum, frame):
            self.stop()
            sys.exit(0)
        signal.signal(signal.SIGINT, stop)

        while True:
            try:
                time.sleep(0x7FFFFFFF)
            except KeyboardInterrupt:
                self.stop()
                break

    @property
    def servers(self):
        servers = {}
        for name in self._servers.keys():
            server = self._servers[name]
            servers[name] = {
                'url': server.url,
                'ticket': server.ticket_create()
            }
        return servers

    @property
    def urls(self):
        return [server.url for server in self._servers.values()]

    def view(self):  # pragma: no cover
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
