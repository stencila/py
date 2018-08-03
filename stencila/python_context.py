import ast
import io
import os
import six
import sys
import traceback

from .value import pack, unpack
from .value import type as type_

import numpy
import pandas

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # pylint: disable=import-error

from .context import Context

undefined = object()

# Global variables that are always available regardless of what
# modules haved been `imported`
#
# See https://stackoverflow.com/a/28050317/4625911 for why
# to use `builtins` modules instead of `__builtin__`
from six.moves import builtins
GLOBALS = dir(builtins)


class PythonContext(Context):

    def __init__(self, *args, **kwargs):
        Context.__init__(self, *args, **kwargs)

        if self._dir:
            os.chdir(self._dir)

        self._variables = {}

    def libraries(self, *args):
        return []

    def list(self, types=[]):
        names = []
        for name, obj in self._variables.items():
            if not len(types) or type_(obj) in types:
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
                if name in ast_visitor.declared or name in GLOBALS:
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
            output_name = None
            if isinstance(last, ast.Assign):
                for target in last.targets:
                    if isinstance(target, ast.Name):
                        output_name = target.id
            elif (
                isinstance(last, ast.FunctionDef) or
                isinstance(last, ast.ClassDef)
            ):
                output_name = last.name
            elif (
                isinstance(last, ast.Import) or
                isinstance(last, ast.ImportFrom)
            ):
                import_name = last.names[0]
                output_name = import_name.asname if import_name.asname else import_name.name

            if output_name:
                cell['outputs'] = [{
                    'name': output_name
                }]

        except Exception as exc:
            cell['messages'].append({
                'type': 'error',
                'message': str(exc),
                'trace': self._get_trace(exc)
            })

        return cell

    def execute(self, cell):
        cell = self.compile(cell)

        try:
            inputs = {}
            for input in cell['inputs']:
                name = input.get('name')
                value = input.get('value')
                if not name:
                    raise RuntimeError('Name is required for input')
                if not value:
                    raise RuntimeError('Value is required for input "%s"' % name)

                if name in self._variables:
                    # Variable name exists in the current context so check
                    # if it needs to be overriden due to changed ownership
                    value_data = value.get('data')
                    if value_data:
                        value_id = value_data.get('id')
                        variable_id = str(id(self._variables.get(name)))
                        if value_id != variable_id:
                            del self._variables[name]
                            inputs[name] = unpack(value)
                else:
                    inputs[name] = unpack(value)

            code = cell['code'].strip()
            try:
                six.exec_(code, inputs, self._variables)
            except RuntimeError as exc:
                cell['messages'].append(self._runtime_error(exc))

            # Evaluate the last line and if no error then make the value output
            # This is inefficient in the sense that the last line is evaluated twice
            # but alternative approaches would appear to require some code parsing
            last = code.split('\n')[-1]
            try:
                output = eval(last, inputs, self._variables)
            except:
                output = undefined

            if output is undefined and len(cell['outputs']):
                # If the last statement was an assignment then grab that variable
                name = cell['outputs'][0]['name']
                if name:
                    output = self._variables.get(name)

            if output is not undefined:
                packed = pack(output)
                if len(cell['outputs']):
                    cell['outputs'][0]['value'] = packed
                else:
                    cell['outputs'] = [{
                        'value': packed
                    }]

            # Clear the current matplotlib figure (if any)
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
        # attribute, subscript, list, tuple etc.
        # We are only interested in name assignment
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.declared.append(target.id)
        # Visit the `value` child node
        self.visit(node.value)

    def visit_For(self, node):
        """
        Visit a `For` node

        At present, don't visit it, avoiding the
        `target` (ie the itertor variable) being treated
        as an input. In the future this should be fixed
        so that proper, variable scoping is accounted for.
        """
        return

    def visit_Name(self, node):
        self.used.append(node.id)
