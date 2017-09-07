import os
import re
import sqlite3
import string

import pandas

from .value import pack, unpack

undefined = object()


class SqliteContext(object):

    def __init__(self, dir=None):
        self._dir = dir

        db = ':memory:'
        if dir:
            dbs = [file for file in os.listdir(dir) if re.match(r'^.*\.(sqlite(3?)|db(3?))$', file)]
            if len(dbs):
                db = os.path.join(dir, dbs[0])

        self._connection = sqlite3.connect(db)

    def runCode(self, code):
        errors = None
        output = undefined
        try:
            if code.lstrip().upper().startswith('SELECT '):
                output = pandas.read_sql_query(code, self._connection)
            else:
                self._connection.execute(code)
        except Exception as exc:
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
        for name, package in inputs.items():
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

SqliteContext.spec = {
    'name': 'SqliteContext',
    'base': 'Context',
    'aliases': ['sql', 'sqlite']
}
