# pylint: disable=superfluous-parens

import atexit
import binascii
import collections
import datetime
import json
import os
import platform
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from .version import __version__
from .host_http_server import HostHttpServer

from .python_context import PythonContext
from .sqlite_context import SqliteContext

# Types of execution contexts provided by this Host
TYPES = {
    'PythonContext': PythonContext,
    'SqliteContext': SqliteContext
}


class Host(object):
    """
    A `Host` allows you to create, get, run methods of, and delete instances of various types.
    The types can be thought of a "services" provided by the host e.g. `PythonContext`,
    `FilesystemStorer`

    The API of a host is similar to that of a HTTP server. It's methods names
    (e.g. `post`, `get`) are similar to HTTP methods (e.g. `POST`, `GET`) but
    the sematics sometimes differ (e.g. a host's `put()` method is used to call an
    instance method)

    A `Host` is not limited to beng served by HTTP and it's methods are exposed by
    `HostHttpServer`. Those other classes are responsible for
    tasks associated with their communication protocol (e.g. serialising and deserialising objects).

    This is a singleton class. There should only ever be one `Host`
    in memory in each process (although, for purposes of testing, this is not enforced)
    """

    def __init__(self):
        self._id = 'py-host-%s' % uuid.uuid4()
        self._key = binascii.hexlify(os.urandom(64)).decode()
        self._servers = {}
        self._started = None
        self._heartbeat = None
        self._instances = {}
        self._counts = {}

    @property
    def id(self):
        """
        Get the identifier of the Host

        :returns: An identification string
        """
        return self._id

    @property
    def key(self):
        """
        Get the seurity key for this Host

        :returns: A key string
        """
        return self._key

    def user_dir(self):
        """
        Get the current user's Stencila data directory.

        This is the directory that Stencila configuration settings, such as the
        installed Stencila hosts, and document buffers get stored.

        :returns: A filesystem path
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
        Get the current Stencila temporary directory.

        :returns: A filesystem path
        """
        return os.path.join(tempfile.gettempdir(), 'stencila')

    def environs(self):
        return [
            {
                "id": "local",
                "name": "local",
                "version": None
            }
        ]

    def types(self):
        return { name: clas.spec for (name, clas) in TYPES.items() }

    def manifest(self):
        """
        Get a manifest for this host.

        The manifest describes the host and it's capabilities. It is used
        by peer hosts to determine which "types" this host provides and
        which "instances" have already been instantiated.

        :returns: A manifest object
        """
        od = collections.OrderedDict
        manifest = od([
            ('id', self._id),
            ('stencila', od([
                ('package', 'py'),
                ('version', __version__)
            ])),
            ('spawn', [sys.executable, '-m', 'stencila', 'spawn']),
            ('environs', self.environs()),
            ('types', self.types())
        ])
        if self._started:
            manifest.update([
                ('process', {'pid': os.getpid()}),
                ('servers', self.servers),
                ('instances', list(self._instances.keys()))
            ])

        return manifest

    def register(self):
        """
        Registration of a host involves creating a file `py.json` inside of
        the user's Stencila data (see `user_dir()`) directory which describes
        the capabilities of this host.
        """
        dir = os.path.join(self.user_dir(), 'hosts')
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(os.path.join(dir, 'py.json'), 'w') as file:
            file.write(json.dumps(self.manifest(), indent=True))

    def startup(self, environ):
        return [{"path": "/"}]

    def shutdown(self, host):
        return True

    def post(self, type, args={}):
        """
        Create a new instance of a type

        :param type: Type of instance
        :param args: Arguments to be passed to type constructor
        :returns: Name of newly created instance
        """
        Class = TYPES.get(type)
        if Class:
            try:
                self._counts[type] += 1
            except KeyError:
                self._counts[type] = 1
            number = self._counts[type]
            name = '%s%s%d' % (type[:1].lower(), type[1:], number)

            args['host'] = self
            args['name'] = name
            instance = Class(**args)

            self._instances[name] = instance
            return name
        else:
            raise Exception('Unknown type: %s' % type)

    def get(self, name):
        """
        Get an instance

        :param name: Name of instance
        :returns: The instance
        """
        instance = self._instances.get(name)
        if instance:
            return instance
        else:
            raise Exception('Unknown instance: %s' % name)

    def put(self, name, method, arg):
        """
        Call a method of an instance

        :param name: Name of instance
        :param method: Name of instance method
        :param kwargs: A dictionary of method arguments
        :returns: Result of method call
        """
        instance = self._instances.get(name)
        if instance:
            try:
                func = getattr(instance, method)
            except AttributeError:
                raise Exception('Unknown method: %s' % method)
            else:
                return func(arg)
        else:
            raise Exception('Unknown instance: %s' % name)

    def delete(self, name):
        """
        Delete an instance

        :param name: Name of instance
        """
        if name in self._instances:
            del self._instances[name]
        else:
            raise Exception('Unknown instance: %s' % name)

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

            # Write content to a secure file only readable by current user
            # Based on https://stackoverflow.com/a/15015748/4625911
            def write_secure(filename, content):
                path = os.path.join(dir, filename)

                # Remove any existing file with potentially elevated mode
                if os.path.isfile(path):
                    os.remove(path)

                # Create a file handle
                mode = stat.S_IRUSR | stat.S_IWUSR  # This is 0o600 in octal.
                umask = 0o777 ^ mode  # Prevents always downgrading umask to 0.
                umask_original = os.umask(0o177)  # 0o777 ^ 0o600
                try:
                    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                finally:
                    os.umask(umask_original)

                # Open file handle and write to file
                with os.fdopen(handle, 'w') as file:
                    file.write(content)

            write_secure(self.id + '.json', json.dumps(self.manifest(), indent=True))
            write_secure(self.id + '.key', self.key)

            if not quiet:
                print('Host has started at: %s' % self._servers['http'].url)

            # On normal process exit, stop this host
            atexit.register(self.stop)

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
            for filename in [self.id + '.json', self.id + '.key']:
                path = os.path.join(self.temp_dir(), 'hosts', filename)
                if os.path.exists(path):
                    os.remove(path)

            if not quiet:
                print('Host has stopped')

    def run(self, address='127.0.0.1', port=2000, authorization=True):
        """
        Start serving this host and wait for connections
        indefinitely
        """
        self.start(address=address, port=port, authorization=authorization)

        print('Use Ctrl+C to stop')

        while True:
            try:
                time.sleep(1000)
            except KeyboardInterrupt:
                self.stop()
                break

    def spawn(self):
        self.start(quiet=True)

        print(json.dumps({
            "id": self.id,
            "key": self.key,
            "manifest": self.manifest()
        }, indent=True))
        sys.stdout.flush()

        # Handle signals if this process is killed somehow
        # (e.g. by a parent peer)
        def stop(signum, frame):
            self.stop(quiet=True)
            sys.exit(0)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        while True:
            time.sleep(1000)

    @property
    def servers(self):
        """
        Get a list of servers for this host.

        Currenty, only a `HostHttpServer` is implemented but in the
        future onther servers for a host may be added (e.g. `HostWebsocketServer`)

        :returns: A dictionary of server details
        """
        servers = {}
        for name in self._servers.keys():
            server = self._servers[name]
            servers[name] = {
                'url': server.url
            }
        return servers

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
