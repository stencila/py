import argparse
import codecs
import json
import mimetypes
import os
import ctypes
import platform
import random
import re
import string
import subprocess
import tempfile
import uuid

import requests

from .version import __version__
from .box import Box, RemoteBox
from .document import Document, RemoteDocument
from .frame import Frame, RemoteFrame
from .sheet import Sheet
from .session import Session, RemoteSession

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


class Instance(object):
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

        self._peers = []

        if config is None:
            self._config = InstanceConfig(self)

        if self._config['startup']['serve']:
            self.serve()

        self.discover()

    @property
    def id(self):
        return self._id

    @property
    def home(self):
        return self._home

    @property
    def logs(self):
        return self._logs

    @property
    def components(self):
        return self._components

    @property
    def token(self):
        return self._token

    @property
    def servers(self):
        return self._servers

    @property
    def peers(self):
        return self._peers

    @staticmethod
    def lengthen(address):
        """
        Lengthen a component address

        :param address: Address to be lengthend
        :returns: lengthend address for the component

        This method lengthen an address shortcut into a fully lengthend address.
        It does not attempt to obtain the component at the address.

        >>> instance.lengthen('./report.docx')
        'file://home/susan/report.docx'

        >>> instance.lengthen('gh/foo/bar/report.md')
        'git://github.com/foo/bar/report.md'

        >>> instance.lengthen('stats/t-test')
        'git://stenci.la/stats/t-test'

        """
        if re.match(r'^[a-z]+://', address):
            return address
        elif address[0] == '+':
            return 'new://' + address[1:]
        elif address[0] == '~':
            return 'id://' + address[1:]
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

    @staticmethod
    def shorten(address):
        if address[:6] == 'new://':
            return '+' + address[6:]
        elif address[:5] == 'id://':
            return '~' + address[5:]
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
            raise RuntimeError('Unable to shortern address\n address: %s' % address)

    @staticmethod
    def split(address):
        """
        Split an address into scheme, path and version parts
        """
        address = Instance.lengthen(address)
        match = re.match(r'([a-z]+)://([\w\-\./]+)(@([\w\-\.]+))?', address)
        if match:
            return match.group(1), match.group(2), match.group(4)
        else:
            raise RuntimeError('Unable to split address\n address: %s' % address)

    def clone(self, address):
        """
        Create a copy of a component and return a path to a local file or directory

        :param address: A component address
        :returns: A local file system path to the component

        Called clone mainly because of `git` and `dat`

        >>> instance.clone('file://home/susan/report.docx')
        '/home/susan/report.docx'

        >>> instance.clone('git://github.com/foo/bar/report.md')
        '/home/joe/.stencila/github.com/foo/bar/master/report.md'

        >>> instance.clone('stats/t-test@1.2.3')
        '/home/joe/.stencila/stats/t-test/1.2.3/'

        """
        scheme, path, version = Instance.split(address)

        if scheme in ('new' 'mem'):
            return None
        elif scheme == 'file':
            if os.path.exists(path):
                return path
            else:
                raise IOError('Local file system path does not exist\n  path: %s' % path)
        elif scheme in ('http', 'https'):
            url = '%s://%s' % (scheme, path)
            response = requests.get(url)
            if response.status_code == 200:
                root, extension = os.path.splitext(path)
                if not extension:
                    type = response.headers.get('Content-Type', None)
                    extension = mimetypes.guess_extension(type)
                handle, path = tempfile.mkstemp(extension)
                with codecs.open(path, 'w', encoding='utf-8') as file:
                    file.write(response.text)
                return path
            else:
                raise IOError(
                    'Unable to get HTTP/S URL\n  url: %s\n  status code: %s\n  message: %s' % (
                        url, response.status_code, response.text
                    )
                )
        elif scheme == 'git':
            match = re.match('([\w\-\.]+)/([\w\-]+/[\w\-]+)/(.+)$', path)
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
            raise RuntimeError('Unable to get address\n  address: %s' % address)

    def register(self, component):
        self._components.append(component)

    def deregister(self, component):
        if component in self._components:
            index = self._components.index(component)
            self._components.pop(index)

    def open(self, address):
        """
        Open a component address
        """
        if address is None:
            return self

        scheme, path, version = self.split(address)

        if scheme == 'new':
            if path == 'document':
                return Document()
            elif path == 'sheet':
                return Sheet()
            elif path == 'frame':
                return Frame()
            elif path == 'session' or path == 'py-session':
                return Session()
            elif path == 'context':
                return Box()
            else:
                raise RuntimeError('Unable to create new component of type\n  address: %s\n  type: %s' % (address, path))

        for component in self._components:
            if scheme == 'id':
                if component.id == path:
                    return component
            else:
                if component.address == scheme + '://' + path:
                    return component

        path = self.clone(address)
        for cls in [Document, Sheet, Frame, Session, Box]:
            component = cls.open(address, path)
            if component is not None:
                return component
        raise RuntimeError('Unable to open a component from the local path\n  address: %s\n path: %s' % (address, path))

        remote = self.ask(address)
        if remote:
            return remote

        raise RuntimeError('Unable to open address\n address: ' + address)

    def show(self, format='html', authenticated=True):
        if format == 'json':
            data = {
                'stencila': self.id,
                'package': 'py',
                'version': __version__
            }
            if authenticated:
                data.update({
                    'components': [dict(type=com.type, address=com.address) for com in self._components],
                    'servers': dict([(type, server.origin) for type, server in self._servers.items()]),
                })
            return json.dumps(data)
        else:
            return '''<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" type="text/css" href="/web/instance.min.css">
    </head>
    <body>
        <script id="data" type="application/json">%s</script>
        <script src="/web/instance.min.js"></script>
    </body>
</html>''' % self.show(format='json')

    def serve(self, types=['http'], real=True):
        if type(types) is list and len(types) > 0:
            try:
                admin = os.getuid() == 0
            except AttributeError:
                admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if admin:
                raise RuntimeError('For security reasons, no servers are started when system admin rights')

            for typ in types:
                if typ not in self._servers:
                    if typ == 'http':
                        server = HttpServer(self)
                    server.serve(on=True, real=real)
                    self._servers[typ] = server
            return self.url()
        else:
            for typ, server in self._servers.iteritems():
                server.serve(on=False, real=real)
            return None

    def url(self, component=None):
        url = self._servers['http'].origin
        if component:
            url += '/' + self.shorten(component.address)
        return url

    def view(self, component=None):
        self.serve()
        url = self.url(component) + '?token=' + self._token
        if platform.system() == 'Linux':
            subprocess.call('2>/dev/null 1>&2 xdg-open "%s"' % url, shell=True)
        else:
            subprocess.call('open "%s"' % url, shell=True)

    def manifest(self):
        return {
            'stencila': True,
            'package': 'py',
            'id': 0,
            'url': self.url(),
            'schemes': ['new'],
            'types': ['document', 'py-session'],
            'formats': ['md']
        }

    def hello(self, manifest):
        return self.manifest()

    def discover(self):
        self._peers = {}
        for port in range(2000, 3000, 10):
            if port != self._servers['http']._port:
                url = 'http://127.0.0.1:%s' % port
                try:
                    response = requests.get(url + '/hello', headers={'Accept': 'application/json'}, timeout=0.1)
                except requests.exceptions.RequestException:
                    pass
                else:
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('stencila'):
                            self._peers[url] = data
        return self._peers

    def ask(self, address):
        for peer in self._peers:
            response = requests.post(peer + '/' + address, headers={'Accept': 'application/json'})
            if response.status_code == 200:
                data = response.json()
                typ = data['type']
                if typ == 'document':
                    return RemoteDocument(peer, data['address'])
                elif typ == 'session':
                    return RemoteSession(peer, data['address'])
                else:
                    raise RuntimeError('Unable to handle a remote component\n  type: %s' % typ)
            else:
                raise RuntimeError('Error\n  message: %s' % response.text)
