from io import BytesIO
from six import exec_
import sys
import traceback

from .component import Component, RemoteComponent


class Session(Component):

    def __init__(self, top=None):
        Component.__init__(self)

        if top is None:
            top = Scope()
        self._scopes = [top]

        self._history = []

    def object(self, name):
        return self._top()[name]

    def objects(self):
        objects = {}
        for name, obj in self._top().items():
            objects[name] = type(obj).__name__
        return objects

    @property
    def history(self):
        return self._history

    def execute(self, code):
        return self._eval(code, exe=True)

    def run(self, code):
        result = self._eval(code, exe=True)
        self._history.append(dict(input=code, output=result))
        return result

    def print_(self, expr):
        result = self._eval(expr)
        if type(result) is dict and 'error' in result:
            return result
        else:
            return str(result)

    def __getattr__(self, name):
        """
        Allow ``print`` to be called as using usual
        name instead of ``print_``
        """
        if name == 'print':
            return self.print_
        else:
            raise AttributeError(name)

    # Shortcut methods for accessing the scope stack

    def _push(self, scope=None):
        # Push a new scope on to the stack
        if scope is None:
            scope = Scope(self.top())
        self._scopes.append(scope)

    def _pop(self):
        # Pop the current scope off the top of the stack
        self._scopes.pop(len(self._scopes)-1)

    def _top(self):
        # Get the top scope in the stack
        return self._scopes[len(self._scopes)-1]

    def _eval(self, code, exe=False):
        try:
            if exe:
                exec_(code, None, self._top())
            else:
                return eval(code, None, self._top())
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # Extract traceback and for compatibility with >=Py3.5 ensure converted to tuple
            frames = [tuple(frame) for frame in traceback.extract_tb(exc_traceback)]
            # Remove first associated with line that executes code above
            frames = frames[1:]
            # If this is Python 2 then also need to remove the frames for the six.exec_ function
            if frames[0][0][-7:] == '/six.py':
                frames = frames[2:]
            # Replace '<string>' with 'code' for file, and '<module>' with '' for function
            # (filename, line number, function name, text)
            trace = []
            for frame in frames:
                trace.append([
                    frame[0].replace('<string>', 'code'),
                    frame[1],
                    frame[2].replace('<module>', ''),
                    '' if frame[3] is None else frame[3]
                ])
            # Get line number from last entry
            line = trace[len(trace)-1][1]
            return {
                'error': exc_type.__name__,
                'message': traceback._some_str(exc_value),
                'line': line,
                'trace': trace
            }
        else:
            return None


class Scope(dict):

    def __init__(self, parent=None):
        self.parent = parent

    def __getitem__(self, name):
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            if self.parent:
                return self.parent[name]
            else:
                raise KeyError(name)


class RemoteSession(RemoteComponent):

    properties = RemoteComponent.properties + [
    ]

    methods = RemoteComponent.methods + [
        'execute', 'print_', 'print'
    ]
