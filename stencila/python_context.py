import ast
import imp
import inspect
import glob
import os
import re
from six import exec_
import sphinxcontrib.napoleon
import sphinxcontrib.napoleon.docstring
import sys
import traceback

from .value import pack, unpack

import numpy
import pandas

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # pylint: disable=import-error

from .context import Context

undefined = object()


class PythonContext(Context):

    def __init__(self, *args, **kwargs):
        Context.__init__(self, *args, **kwargs)

        if self._dir:
            os.chdir(self._dir)

        self._scope = {}

        self._global_scope = {
            'numpy': numpy,
            'np': numpy,
            'matplotlib': matplotlib,
            'plt': plt,
            'pandas': pandas,
            'pd': pandas
        }

    def getLibraries(self):
        # TODO: return registered function libraries
        return []

    def list(self, types=[]):
        names = []
        for name, obj in self._scope.items():
            if not len(types) or self.type(obj) in types:
                names.append(name)
        return names

    def compile(self, operation):
        """
        Compile an operation

        :returns: A dictionary with ``messages`` and a compiled ``operation``
        """
        messages = []
        # Try block to ensure that any exceptions are converted into a
        # runtime error message
        try:
            type = operation.get('type')
            if type == 'cell':
                operation, messages = self.compile_cell(operation)
            elif type == 'func':
                operation, messages = self.compile_func(operation)
            else:
                messages = [{
                    'type': 'error',
                    'message': 'PythonContext can not compile operations of type "%s"' % type
                }]
        except Exception as exc:
            messages = [{
                'type': 'error',
                'message': str(exc)
            }]

        return {
            'messages': messages,
            'operation': operation
        }

    def compile_cell(self, cell):
        inputs = {}
        outputs = {}

        # TODO: analysis of tree to determine inputs and outputs
        # tree = ast.parse(code, mode='exec')

        cell['inputs'] = inputs
        cell['outputs'] = outputs
        return cell, messages

    def compile_func(self, func=None, file=None, dir=None):
        """
        Compile a ``func`` operation

        Parses the source of the function (either a string or a file
        path) to extract it's ``description``, ``param``, ``return`` etc
        properties.

        >>> context.compile_func({
        >>>     'type': 'func',
        >>>     'source': 'def hello(who): return "Hello Hello %s!" % who'
        >>> })
        {
            'type': 'func',
            'name': 'hello',
            'source': 'def hello(): return "Hello Hello %s!" % who'
            'params': [{
                'name': 'who'
            }],
            ...
        }


        Parameters
        ----------
            func : dict or string
                A ``func`` operation. If a string is supplied then an operation
                object is created with the ``source`` property set to
                the string.

        Returns
        -------
            func : dict
                The compiled ``func`` operation
            messages : list
                A list of messages (e.g errors)
        """
        messages = []

        if func is None:
            if file:
                with open(file) as file_obj:
                    func, messages = self.compile_func({
                        'type': 'func',
                        'source': file_obj.read()
                    })
                return func, messages
            elif dir:
                count  =0
                for file in glob.glob(dir + '/*.py'):
                    self.compile_func(file=file)
                    count += 1
                return count
            else:
                raise RuntimeError('No function provided to compile!')
        elif callable(func):
            func_obj = func
            func = {
                'type': 'func',
                'source': '\n'.join(inspect.getsourcelines(func_obj)[0]).strip()
            }
            func_name = func_obj.__code__.co_name
        else:
            # If necessary, wrap string arguments into an operation dict
            if isinstance(func, str) or isinstance(func, bytes):
                func = {
                    'type': 'func',
                    'source': func
                }

            # Obtain source code
            source = func.get('source')
            if not source:
                raise RuntimeError('Not function source code specified in `source` or `file` properties')

            # Parse function source and extract properties from the Function object
            scope = {}
            exec_(source, scope)

            # Get name of function
            names = [key for key in scope.keys() if not key.startswith('__')]
            if len(names) > 1:
                messages.append({
                    'type': 'warning',
                    'message': 'More than one function or object defining in function source: %s' % names
                })
            func_name = names[-1]
            func_obj = scope[func_name]

        # Extract parameter specifications
        func_spec = inspect.getargspec(func_obj)
        args = func_spec.args
        if func_spec.varargs:
            args.append(func_spec.varargs)
        if func_spec.keywords:
            args.append(func_spec.keywords)
        params = []
        for index, name in enumerate(args):
            param = {
                'name': name
            }
            if name == func_spec.varargs:
                param['repeat'] = True
            elif name == func_spec.keywords:
                param['extend'] = True
            if func_spec.defaults:
                defaults_index = len(args) - len(func_spec.defaults) + index
                if defaults_index > -1:
                    default = func_spec.defaults[defaults_index]
                    param['default'] = {
                        'type': Context.type(default),
                        'data': default
                    }
            params.append(param)

        # Get docstring and parse it for extra parameter specs
        docstring = func_obj.__doc__
        docstring_params = {}
        docstring_returns = {}
        if docstring:
            docstring = trim_docstring(docstring)
            config = sphinxcontrib.napoleon.Config(napoleon_use_param=True, napoleon_use_rtype=True)
            docstring = sphinxcontrib.napoleon.docstring.NumpyDocstring(docstring, config, what='function').lines()
            docstring = sphinxcontrib.napoleon.docstring.GoogleDocstring(docstring, config, what='function').lines()

            summary = docstring[0]
            description = ''
            pattern = re.compile(r'^:(param|returns|type|rtype)(\s+(\w+))?:(.*)$')
            for line in docstring[1:]:
                match = pattern.match(line)
                if match:
                    type = match.group(1)
                    name = match.group(3)
                    desc = match.group(4).strip()
                    if type == 'param':
                        param = docstring_params.get(name, {})
                        param['description'] = desc
                        docstring_params[name] = param
                    elif type == 'type':
                        param = docstring_params.get(name, {})
                        param['type'] = desc
                        docstring_params[name] = param
                    elif type == 'returns':
                        docstring_returns['description'] = desc
                    elif type == 'rtype':
                        docstring_returns['type'] = desc
                else:
                    description += line + '\n'
            description = description.strip()

            if len(summary):
                func.update({'summary': summary})

            if len(description):
                func.update({'description': description})

            for name, spec in docstring_params.items():
                for index, param in enumerate(params):
                    if param['name'] == name:
                        params[index].update(spec)
                        break

            if len(docstring_returns):
                func.update({'returns': docstring_returns})

        func.update({
            'name': func_name,
            'params': params
        })

        # Register the function in scope
        self._scope[func_name] = func_obj

        return func, messages

    def execute(self, code, inputs={}):
        # Extract names and values of inputs
        names = inputs.keys()
        values = [unpack(package) for package in inputs.values()]

        # Execute the code
        errors = None
        try:
            exec_(code, self._global_scope)
        except:
            errors = self._errors()

        # Check for 'artifacts'
        artifact = None
        # matplotlib figure
        figure = plt.gcf()
        if len(figure.get_axes()):
            artifact = figure
            plt.clf()

        output = undefined
        if not errors:
            # Evaluate the last line and if no error then make the value output
            # This is inefficient in the sense that the last line is evaluated twice
            # but alternative approaches would appear to require some code parsing
            last = code.split('\n')[-1]
            try:
                output = eval(last, self._global_scope)
            except:
                output = undefined

            # If output is undefined and there was an artifact (e.g. a matplotlib figure)
            # then use the artifact value as output
            if output is undefined and artifact:
                output = artifact

            # Errors should be a list
            errors = []

        return {
            'messages': errors,
            'value': None if output is undefined else pack(output)
        }

    def _errors(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        # Extract traceback and for compatibility with >=Py3.5 ensure converted to tuple
        frames = [tuple(frame) for frame in traceback.extract_tb(exc_traceback)]
        # Remove first associated with line that executes code above
        frames = frames[1:]
        # If this is Python 2 then also need to remove the frames for the six.exec_ function
        if len(frames) and frames[0][0][-7:] == '/six.py':
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
        if len(trace):
            line = trace[-1][1]
        else:
            # No trace when syntax error
            line = 0

        return [{
            'type': 'error',
            'line': line,
            'column': 0,
            'message': exc_type.__name__ + ': ' + traceback._some_str(exc_value)
        }]

PythonContext.spec = {
    'name': 'PythonContext',
    'client': 'ContextHttpClient'
}


def trim_docstring(docstring):
    """From https://www.python.org/dev/peps/pep-0257/"""
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)
