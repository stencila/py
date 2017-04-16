from six import exec_
import sys
import traceback

from value import pack

undefined = object()


class PythonContext(object):

    def __init__(self):
        self.global_scope = PythonContextScope()

    def runCode(self, code):
        # Execute the code
        errors = None
        try:
            exec_(code, self.global_scope)
        except:
            errors = self._errors()

        output = undefined
        if not errors:
            # Evaluate the last line and if no error then make the value output
            # This is inefficient in the sense that the last line is evaluated twice
            # but alternative approaches would appear to require some code parsing
            last = code.split('\n')[-1]
            try:
                output = eval(last, self.global_scope)
            except:
                output = undefined

        return {
            'errors': errors,
            'output': None if output is undefined else pack(output)
        }

    def _errors(self):
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
        return [{
            'line': line,
            'column': 0,
            'message': exc_type.__name__ + ': ' + traceback._some_str(exc_value)
        }]


class PythonContextScope(dict):

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
