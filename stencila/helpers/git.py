import os
import subprocess
import tempfile
import zipfile


class Git:
    """
    Helps with Git workflow tasks
    """

    def __init__(self, path=None):
        """
        Initialise a Git repository helper

        :pram path: Path to the repository
        """
        self.path = path

    def __call__(self, *args):
        """
        Call Git

        Mostly used internally.
        Prepends git directory and working directory to prevent
        the need to change directory.
        """
        args = list(args)
        if self.path:
            args = [
                '--git-dir=%s' % os.path.join(self.path, '.git'),
                '--work-tree=%s' % self.path
            ] + args
        process = subprocess.Popen(
            ['git'] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = process.communicate()
        if process.returncode:
            raise RuntimeError('Error calling Git\n  return code: %s\n message: %s\n  arguments: %s' % (process.returncode, err, args))
        else:
            return out

    def clone(self, url, dir):
        """
        Clone a Git repository

        :param url: The HTTP/S URL to clone from
        :param dir: The directory to clone to
        """
        return self('clone', url, dir)

    def exists(self, object):
        """
        Check an object exists in the repository

        :param object: A Git object string
        :returns: True if the object exists, False otherwise

        Analagous to ``git cat-file -e <object>``

        >>> # Check that a commit exists
        >>> repo.exists('d0dd1f6')

        >>> # Check that a file exists at that commit
        >>> repo.exists('d0dd1f6:README.md')
        """
        try:
            self('cat-file', '-e', object)
        except RuntimeError:
            return False
        else:
            return True

    def type(self, object):
        """
        Get the type of a Git object

        :param object: A Git object string
        :returns: The type of the object (`'commit'`, `'tree'`, `'blob'` or `'tag'`)
                  or `None` if the object does not exist

        Analagous to ``git cat-file -t <object>``

        >>> repo.type('d0dd1f6:README.md') == 'blob'
        """
        return self('cat-file', '-t', object)

    def pull(self, *args):
        """
        Fetch from and integrate with another repository or a local branch

        Analagous to ``git pull``
        """
        self('pull', *args)

    def export(self, dir, version='HEAD'):
        """
        Export the repository's working tree to another directory

        :param dir: The directory to export to
        :param version: The version to export (e.g. ``HEAD``, ``d5ab42``)
        """
        dir = os.path.abspath(dir)
        handle, zipfilename = tempfile.mkstemp()
        self('archive', '--format=zip', '--output=%s' % zipfilename, version)
        with zipfile.ZipFile(zipfilename, 'r') as file:
            file.extractall(dir)

git = Git()
