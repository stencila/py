import os

from .component import Component


class Environ(Component):

    @staticmethod
    def open(address, path):
        if os.path.isdir(path):
            return Environ(address, path)
        return None

    def __init__(self, address=None, path=None):
        address = '.'
        Component.__init__(self, address, path)

    def read(self, path=''):
        path = Component.read(self, path)

        return self

    def write(self, path=''):
        path = Component.write(self, path)

        return self
