import sqlite3
import string

import pandas

from .value import pack, unpack

undefined = object()


class SqliteContext(object):

    def __init__(self):
        self._connection = sqlite3.connect(':memory:')

    def runCode(self, code):
        errors = None
        output = undefined
        try:
            if code.lstrip().upper().startswith('SELECT '):
                output = pandas.read_sql_query(code, self._connection)
            else:
                self._connection.execute(code)
        except Exception, exc:
            errors = [{
                'line': 0,
                'column': 0,
                'message': str(exc)
            }]

        return {
            'errors': errors,
            'output': None if output is undefined else pack(output)
        }

    def callCode(self, code, inputs={}):
        variables = {}
        for name, package in inputs.iteritems():
            value = unpack(package)
            if isinstance(value, pandas.DataFrame):
                value.to_sql(name, self._connection, flavor='sqlite', if_exists='replace', index=False)
            elif type(value) == list:
                variables[name] = tuple(value)
            else:
                variables[name] = value

        # Non-table inputs are available as text substitution variables
        code_ = string.Template(code).substitute(variables)

        return self.runCode(code_)
