import argparse
from six.moves import builtins
import json
import mimetypes
import os
import platform
import random
import re
import string
import subprocess
import tempfile
import uuid

import requests

from .version import __version__
from .document import Document
from .sheet import Sheet
from .session import Session
from .environ import Environ
from .helpers.git import git, Git
from .helpers import yaml_ as yaml
from .servers.http import HttpServer
from .utilities import update
from . import instance_


class InstanceConfig(dict):

    def __init__(self, instance):
        # Defaults
        self['startup'] = {
            'serve': True
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


class Instance:
    """
    The Stencila instance.

    Orchestrates ``Components`` and encapsulates application state.
    This is a singleton class; there should only ever be one ``Instance``
    in memory in each Python process (although this is not enforced for purposes of testing)
    """

    def __init__(self, config=None):
        """
        Inititalise the instance


        """
        if not instance_.instance:
            instance_.instance = self

        self._id = str(uuid.uuid1())

        self._home = os.path.join(os.path.expanduser('~'), '.stencila')
        self._logs = os.path.join(self._home, '.logs')
        if not os.path.exists(self._logs):
            os.makedirs(self._logs)

        self._components = []

        self._token = ''.join(
            [random.choice(string.ascii_letters+string.digits) for i in range(12)]
        )
        self._servers = {}

        if config is None:
            self._config = InstanceConfig(self)

        self._session = Session()
        self._environ = Environ()

        if self._config['startup']['serve']:
            self.serve()

    @property
    def id(self):
        return self._id

    @property
    def home(self):
        return self._home

    @property
    def logs(self):
        return self._logs

    def resolve(self, address):
        """
        Resolve a component address

        :param address: Address to be resolved
        :returns: Resolved address for the component

        This method resolve an address shortcut into a fully resolved address.
        It does not attempt to obtain the component at the address.

        >>> resolve('./report.docx')
        'file://home/susan/report.docx'

        >>> resolve('gh/foo/bar/report.md')
        'git://github.com/foo/bar/report.md'

        >>> resolve('stats/t-test')
        'git://stenci.la/stats/t-test'

        """
        # full
        if address[:6] == 'mem://':
            return address
        elif address[:7] == 'file://':
            return address
        elif address[:7] == 'http://' or address[:8] == 'https://':
            return address
        elif address[:6] == 'git://':
            return address
        # shortened
        elif address[0] == '~':
            return 'mem://' + address[1:]
        elif address[0] == '.' or address[0] == '/':
            return 'file://' + os.path.abspath(address)
        elif address[:3] == 'bb/':
            return 'git://bitbucket.org/' + address[3:]
        elif address[:3] == 'gh/':
            return 'git://github.com/' + address[3:]
        elif address[:3] == 'gl/':
            return 'git://gitlab.com/' + address[3:]
        else:
            return 'git://stenci.la/' + address

    def shorten(self, address):
        address = self.resolve(address)
        if address[:6] == 'mem://':
            return '~' + address[6:]
        elif address[:7] == 'file://':
            return address[7:]
        elif address[:7] == 'http://' or address[:8] == 'https://':
            return address
        elif address[:20] == 'git://bitbucket.org/':
            return 'bb/' + address[20:]
        elif address[:17] == 'git://github.com/':
            return 'gh/' + address[17:]
        elif address[:17] == 'git://gitlab.com/':
            return 'gl/' + address[17:]
        elif address[:16] == 'git://stenci.la/':
            return address[16:]
        else:
            raise RuntimeError('Unrecognised address\n address: %s' % address)

    def obtain(self, address, version=None):
        """
        Obtain a component

        :param address: A component address
        :returns: A local file system path to the component

        Returns a file system path to a file or directory

        >>> obtain('file://home/susan/report.docx')
        '/home/susan/report.docx'

        >>> obtain('git://github.com/foo/bar/report.md')
        '/home/joe/.stencila/github.com/foo/bar/master/report.md'

        >>> obtain('git://stenci.la/stats/t-test', '1.2.3')
        '/home/joe/.stencila/stats/t-test/1.2.3/'

        Used by other ``Component`` methods when loading content.

        """
        address = self.resolve(address)
        path = None

        if address[:6] == 'mem://':
            return None
        elif address[:7] == 'file://':
            path = address[7:]
            if os.path.exists(path):
                return path
            else:
                raise IOError('Filesystem path does not exist\n  address: %s\n  path: %s' % (address, path))
        elif address[:7] == 'http://' or address[:8] == 'https://':
            response = requests.get(address)
            if response.status_code == 200:
                root, extension = os.path.splitext(address)
                if not extension:
                    type = response.headers.get('Content-Type', None)
                    extension = mimetypes.guess_extension(type)
                handle, path = tempfile.mkstemp(extension)
                with builtins.open(path, 'w') as file:
                    file.write(response.text.encode('utf-8'))
                return path
            else:
                raise IOError(
                    'Unable to obtain HTTP address\n  address: %s\n  status code: %s\n  message: %s' % (
                        address, response.status_code, response.text
                    )
                )
        elif address[:6] == 'git://':
            match = re.match('git://([\w\-\.]+)/([\w\-]+/[\w\-]+)/(.+)$', address)
            if match:
                host = match.group(1)
                if host == 'stenci.la':
                    host_dir = ''
                else:
                    host_dir = host

                repo = match.group(2)
                repo_dir = os.path.join(self._home, host_dir, repo)
                master_dir = os.path.join(repo_dir, 'master')
                if not os.path.exists(master_dir):
                    url = 'https://%s/%s.git' % (host, repo)
                    #info('Cloning repository\n  url: %s\n  directory: %s' % (url, master_dir))
                    git.clone(url, master_dir)

                if version and version != 'master':
                    repo = Git(master_dir)
                    if not repo.exists(version):
                        #info('Updating repository\n directory: %s' % repo_dir)
                        repo.pull()
                        if not repo.exists(version):
                            raise RuntimeError('Version does not exist in the repository\n  repository: %s\n  version: %s' % (repo_dir, version))
                    version_dir = os.path.join(repo_dir, version)
                    repo.export(version_dir, version)
                else:
                    version_dir = master_dir

                file = match.group(3)
                path = os.path.join(version_dir, file)
                if not os.path.exists(path):
                    raise IOError('Path does not exist\n  path: %s' % path)
                return path
            else:
                raise RuntimeError('Unable to determine Git repository URL from address\n  address: %s' % address)
        else:
            raise RuntimeError('Unhandled address\n  address: %s' % address)

    def register(self, component):
        self._components.append(component)

    @property
    def components(self):
        return self._components

    def provide(self, address):
        address = self.resolve(address)
        for component in self._components:
            if component.address == address:
                return component
        return None

    def deregister(self, component):
        if component in self._components:
            index = self._components.index(component)
            self._components.pop(index)

    def new(self, type):
        if type == 'document':
            return Document()
        elif type == 'sheet':
            return Sheet()
        elif type == 'session':
            return Session()
        elif type == 'environ':
            return Environ()
        else:
            raise RuntimeError('Unhandled component type\n  type: %s' % type)

    def open(self, address):
        component = self.provide(address)
        if component:
            return component

        path = self.obtain(address)
        if path is None:
            addresses = [com.address for com in self._components]
            raise RuntimeError('Not able to find in-memory component\n  address: %s\n  addresses: %s' % (address, addresses))

        for type in [Document, Sheet, Session, Environ]:
            component = type.open(address, path)
            if component is not None:
                return component

        raise RuntimeError('Not able to determine component type from path\n  path: %s' % path)

    @property
    def token(self):
        return self._token

    def serve(self, types=['http'], real=True):
        if type(types) is list and len(types) > 0:
            for typ in types:
                if typ not in self._servers:
                    if typ == 'http':
                        server = HttpServer(self)
                    server.serve(on=True, real=real)
                    self._servers[typ] = server
            return self._servers['http'].origin
        else:
            for typ, server in self._servers.iteritems():
                server.serve(on=False, real=real)
            return None

    def summary(self):
        return {
            'stencila': self.id,
            'package': 'py',
            'version': __version__
        }

    def manifest(self):
        manifest = self.summary()
        manifest.update({
            'components': [(com.type, com.address) for com in self._components],
            'servers': dict([(type, server.origin) for type, server in self._servers.items()]),
        })
        return manifest

    def page(self, authenticated=True):
        if not authenticated:
            data = self.summary()
        else:
            data = self.manifest()

        return '''<!DOCTYPE html>
    <html>
        <head>
            <link rel="stylesheet" type="text/css" href="/web/instance.min.css">
        </head>
        <body>
            <script id="data" type="application/json">%(data)s</script>
            <script src="/web/instance.min.js"></script>
        </body>
    </html>''' % {
            'data': json.dumps(data)
        }

    def view(self, component=None):
        self.serve()
        url = self._servers['http'].origin + '/'
        if component:
            url += component.address
        url += '?token=' + self._token
        if platform.system() == 'Linux':
            subprocess.call('2>/dev/null 1>&2 xdg-open "%s"' % url, shell=True)
        else:
            subprocess.call('open "%s"' % url, shell=True)
