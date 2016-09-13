from .component import Component


class Context(Component):

    def read(self, path=''):
        path = Component.read(self, path)

        return self

    def write(self, path=''):
        path = Component.write(self, path)

        return self