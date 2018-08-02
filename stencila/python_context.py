import ast
import io
import inspect
import glob
import os
import re
import six
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

        self._globals = {}

        self._variables = {}

    def libraries(self, *args):
        return []

    def list(self, types=[]):
        names = []
        for name, obj in self._scope.items():
            if not len(types) or self.type(obj) in types:
                names.append(name)
        return names

    def compile(self, cell):
        """
        Compile a cell

        :returns: A compiled ``cell``
        """
        cell = Context.compile(self, cell)

        try:
            # Ensure this is a Python cell
            if cell['lang'] and cell['lang'] != 'py':
                raise RuntimeError('Cell code must be Python code')
            else:
                cell['lang'] = 'py'

            # If the cell's code is empty, just return
            code = cell['code'].strip()
            if code == '':
                return cell

            # Parse the code and catch any syntax errors
            try:
                tree = ast.parse(code, mode='exec')
            except SyntaxError as exc:
                cell['messages'].append({
                    'type': 'error',
                    'message': str(exc),
                    'line': getattr(exc, 'lineno', 0),
                    'column': getattr(exc, 'offset', 0)
                })
                return cell

            # Walk the AST to dtermine dependencies
            ast_visitor = CompileAstVisitor(tree)
            for name in ast_visitor.used:
                if name in ast_visitor.declared or name in self._globals:
                    continue
                present = False
                for input in cell['inputs']:
                    if input.get('name') == name:
                        present = True
                        break
                if not present:
                    cell['inputs'].append({
                        'name': name
                    })

            # Determine the output from the last statement in the AST
            last = tree.body[-1]
            if isinstance(last, ast.Assign):
                for target in last.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        cell['outputs'] = [{
                            'name': name
                        }]

        except Exception as exc:
            cell['messages'].append({
                'type': 'error',
                'message': str(exc),
                'trace': self._get_trace(exc)
            })

        return cell

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
            six.exec_(source, scope)

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

    def execute(self, cell):
        cell = self.compile(cell)

        try:
            locals = {}
            for input in cell['inputs']:
                name = input.get('name')
                value = input.get('value')
                if not name:
                    raise RuntimeError('Name is required for input')
                if not value:
                    raise RuntimeError('Value is required for input "%s"' % name)
                if name in self._variables:
                    value = self._variables[name]
                else:
                    value = unpack(value)
                locals[name] = value

            code = cell['code'].strip()
            try:
                six.exec_(code, self._globals, locals)
            except RuntimeError as exc:
                cell['messages'].append(self._runtime_error(exc))

            # Evaluate the last line and if no error then make the value output
            # This is inefficient in the sense that the last line is evaluated twice
            # but alternative approaches would appear to require some code parsing
            last = code.split('\n')[-1]
            try:
                output = eval(last, self._globals, locals)
            except:
                output = undefined

            if output is undefined and len(cell['outputs']):
                # If the last statement was an assignment then grab that variable
                name = cell['outputs'][0]['name']
                if name:
                    output = locals.get(name)

            if output is not undefined:
                packed = pack(output)
                if len(cell['outputs']):
                    cell['outputs'][0]['value'] = packed
                else:
                    cell['outputs'] = [{
                        'value': packed
                    }]

            # Clear the current matplot figure (if any)
            # after any plot has been packed as an output
            plt.clf()

        except Exception as exc:
            cell['messages'].append({
                'type': 'error',
                'message': str(exc),
                'trace': self._get_trace(exc)
            })

        return cell

    def _runtime_error(self):
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

        return {
            'type': 'error',
            'line': line,
            'column': 0,
            'message': exc_type.__name__ + ': ' + traceback._some_str(exc_value)
        }

    def _get_trace(self, exc):
        stream = io.StringIO() if six.PY3 else io.BytesIO()
        traceback.print_exc(file=stream)
        return stream.getvalue()

PythonContext.spec = {
    'name': 'PythonContext',
    'client': 'ContextHttpClient'
}


class CompileAstVisitor(ast.NodeVisitor):
    # Use ast.dump to find out about structure of node types
    # > import ast
    # > ast.dump(ast.parse('x=1').body[0])
    # "Assign(targets=[Name(id='x', ctx=Store())], value=Num(n=1))"

    def __init__(self, tree):
        self.declared = []
        self.used = []
        self.visit(tree)

    def aliases(self, aliases):
        for alias in aliases:
            name = alias.asname if alias.asname else alias.name
            self.declared.append(name)

    def visit_Import(self, node):
        self.aliases(node.names)

    def visit_ImportFrom(self, node):
        self.aliases(node.names)

    def visit_Global(self, node):
        for name in node.names:
            self.declared.append(name)

    def visit_FunctionDef(self, node):
        # Do not visit function body
        self.declared.append(node.name)

    def visit_ClassDef(self, node):
        # Do not visit class body
        self.declared.append(node.name)

    def visit_Assign(self, node):
        # There are various forms of assignment including
        # attribute, subscript, list, tupe etc.
        # We are only interested in name assignment
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.declared.append(target.id)

    def visit_Name(self, node):
        self.used.append(node.id)


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
