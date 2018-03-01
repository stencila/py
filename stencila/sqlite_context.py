import os
import re
import sqlite3
import string

import pandas

from .context import Context


class SqliteContext(Context):

    def __init__(self, *args, **kwargs):
        Context.__init__(self, *args, **kwargs)

        db = ':memory:'
        if self._dir:
            dbs = [file for file in os.listdir(self._dir) if re.match(r'^.*\.(sqlite(3?)|db(3?))$', file)]
            if len(dbs):
                db = os.path.join(self._dir, dbs[0])

        self._connection = sqlite3.connect(db)

    def compile(self, operation):
        """
        Compile an operation

        :returns: A dictionary with ``messages`` and a compiled ``operation``
        """
        if isinstance(operation, basestring):
            operation = {
                'type': 'cell',
                'code': operation
            }

        messages = []

        type = operation.get('type')
        if type == 'cell':
            inputs = {}
            outputs = {}

            operation['inputs'] = inputs
            operation['outputs'] = outputs
        else:
            messages.append({
                'type': 'error',
                'message': 'SqliteContext can not compile operations of type "%s"' % type
            })

        return {
            'messages': messages,
            'operation': operation
        }

    def execute(self, operation):
        if isinstance(operation, basestring):
            result = self.compile(operation)
            operation = result['operation']
            messages = result['messages']
        else:
            messages = []
        value = None

        type = operation.get('type')
        if type == 'cell':
            # Non-table cell inputs are available as text substitution variables
            variables = {}
            for name, packed in operation['inputs'].items():
                data = self.unpack(name, packed)
                if isinstance(data, str) and str[:7] == '_table_':
                    pass
                elif type(data) == list:
                    # Transform lists to tuples so that they are rendered to SQL
                    # with parentheses instead of square brackets
                    variables[name] = tuple(data)
                else:
                    variables[name] = data
            sql = string.Template(operation['code']).substitute(variables)

            if sql:
                # If the "assign" SQL extension is used then transform the SQL
                select = None
                match = re.match('^\s*(\w+)\s*=\s*\b(SELECT\b.*)', sql)
                if match:
                    value = match.group(1)
                    select = match.group(2)
                elif sql.lstrip().upper().startswith('SELECT '):
                    value = 'temp_table'
                    select = sql
                if select:
                    sql = 'DROP TABLE IF EXISTS %s; CREATE TEMPORARY TABLE %s AS %s' % (value, value, select)

                print((value, sql))

                try:
                    self._connection.executescript(sql)
                except Exception as exc:
                    messages.append({
                        'type': 'error',
                        'line': 0,
                        'column': 0,
                        'message': str(exc)
                    })
                else:
                    if value:
                        value = self.pack(value)
        else:
            messages.append({
                'type': 'error',
                'message': 'SqliteContext can not execute operation of type "%s"' % type
            })

        return {
            'messages': messages,
            'value': value
        }

    def pack(self, data, max_rows=30):
        """
        Pack data into a data package or data pointer

        Currently this context only deals with tables and chooses to create
        a package or a pointer based on the number of rows in the table

        :param data: Name of the table to pack
        """
        rows = self._connection.execute('SELECT count(*) FROM %s' % data).fetchone()[0]
        if rows <= max_rows:
            data_frame = pandas.read_sql_query('SELECT * FROM %s' % data, self._connection)
            return Context.pack(data_frame)
        else:
            # Return a pointer
            return {
                'type': 'table',
                'host': self._host.servers['http'],
                'context': self._name,
                'name': data
            }

    def unpack(self, packed, name):
        data = None
        return data

    def fetch(self, name, options={}):
        # TODO implement options e.g. pagination
        data_frame = pandas.read_sql_query('SELECT * FROM %s' % name, self._connection)
        return Context.pack(data_frame)


SqliteContext.spec = {
    'name': 'SqliteContext',
    'client': 'ContextHttpClient'
}
