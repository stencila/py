from io import BytesIO
from six import exec_
import sys
import traceback

import pystache

from .component import Component


class Session(Component):

    def __init__(self, top=None):
        Component.__init__(self)

        if top is None:
            top = Scope()
        self._scopes = [top]

        self._history = []

    def objects(self):
        objects = {}
        for name, obj in self._top().items():
            objects[name] = type(obj).__name__
        return objects

    @property
    def history(self):
        return self._history


    def execute(self, code):
        try:
            exec_(code, None, self._top())
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.extract_tb(exc_traceback)
            # Remove first 3 trace entrries assocociated with executing code
            tb = tb[3:]
            # Replace '<string>' with 'code' for file, and '<module>' with '' for function
            # (filename, line number, function name, text)
            trace = []
            for line in tb:
                trace.append([
                    line[0].replace('<string>', 'code'),
                    line[1],
                    line[2].replace('<module>', ''),
                    line[3]
                ])
            # Get line number from last entry
            line = trace[len(trace)-1][1]
            result = {
                'line': line,
                'type': exc_type.__name__,
                'info': repr(exc_value),
                'trace': trace
            }
        else:
            result = None

        self._history.append(dict(input=code, output=result))

        return result

    def text(self, expr):
        return str(self._eval(expr))

    def content(self, format='html'):
        return pystache.render('''
<ul>
    {{#objects}}
        <li>
            <span class="name">{{name}}<span>
            <span class="type">{{type}}</span>
        </li>
    {{/objects}}
</ul>
<ol>
    {{#history}}
        <li><pre><code>{{input}}</code></pre><pre><code>{{output}}</code></pre></li>
    {{/history}}
</ol>
        ''', {
            'objects': [dict(name=name, type=type) for name, type in self.objects().items()],
            'history': self.history
        })


    def write(self):
        # Pickle
        pass

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

    def _eval(self, expr):
        # Evaluate an expr in the top of the stack
        return eval(expr, {}, self._top())


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
