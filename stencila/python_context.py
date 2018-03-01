import ast
import imp
import os
from six import exec_
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

    def compile(self, code):
        # TODO: analysis of tree to determine inputs and outputs
        # tree = ast.parse(code, mode='exec')
        inputs = []
        output = None
        messages = []
        return {
            'inputs': inputs,
            'output': output,
            'messages': messages
        }

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
