import errno
import mimetypes
import os
import re
import tempfile

import requests

from .messages import info
from .helpers.git import Git, git


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

#: The Stencila home folder on the local computer
home = os.path.join(os.path.expanduser('~'), '.stencila')


def resolve(address):
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
    if address[:7] == 'file://':
        return address
    elif address[:7] == 'http://' or address[:8] == 'https://':
        return address
    elif address[:6] == 'git://':
        return address
    elif address[0] == '.' or address[0] == '/':
        return 'file://' + os.path.abspath(address)
    elif address[:3] == 'bb/' or address[:10] == 'bitbucket/':
        return 'git://bitbucket.org/' + address[3:]
    elif address[:3] == 'gh/' or address[:7] == 'github/':
        return 'git://github.com/' + address[3:]
    elif address[:3] == 'gl/' or address[:7] == 'gitlab/':
        return 'git://gitlab.com/' + address[3:]
    else:
        return 'git://stenci.la/' + address


def obtain(address, version=None):
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
    address = resolve(address)
    path = None

    if address[:7] == 'file://':
        path = address[7:]
        if os.path.exists(path):
            return path
        else:
            raise IOError('Filesystem path does not exist\n  address: %s' % address)
    elif address[:7] == 'http://' or address[:8] == 'https://':
        response = requests.get(address)
        if response.status_code == 200:
            root, extension = os.path.splitext(address)
            if not extension:
                type = response.headers.get('Content-Type', None)
                extension = mimetypes.guess_extension(type)
            handle, path = tempfile.mkstemp(extension)
            with open(path, 'w') as file:
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
            if host != 'stenci.la':
                host_dir = host

            repo = match.group(2)
            repo_dir = os.path.join(home, host_dir, repo)
            master_dir = os.path.join(repo_dir, 'master')
            if not os.path.exists(master_dir):
                url = 'https://%s/%s.git' % (host, repo)
                info('Cloning repository\n  url: %s\n  directory: %s' % (url, master_dir))
                git.clone(url, master_dir)

            if version and version != 'master':
                repo = Git(master_dir)
                if not repo.exists(version):
                    info('Updating repository\n directory: %s' % repo_dir)
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