import pandas

from stencila.sqlite_context import SqliteContext
from stencila.value import pack


def test_new():
    c = SqliteContext()

    assert isinstance(c, SqliteContext)


def test_runCode():
    c = SqliteContext()

    assert c.runCode('') == {'errors': None, 'output': None}

    assert c.runCode('SELECT 42 AS x') == {'errors': None, 'output': pack(pandas.DataFrame([{'x': 42}]))}

    err = c.runCode('foo')['errors'][0]
    assert err['line'] == 0
    assert err['message'] == 'near "foo": syntax error'

    err = c.runCode('SELECT col FROM foo')['errors'][0]
    assert err['line'] == 0
    assert err['message'] == "Execution failed on sql 'SELECT col FROM foo': no such table: foo"


def test_callCode():
    c = SqliteContext()

    table = pandas.DataFrame({'x': [1, 2, 3, 4, 5]})

    assert c.callCode('') == {'errors': None, 'output': None}

    assert c.callCode('SELECT * FROM data', {'data': pack(table)}) == {'errors': None, 'output': pack(table)}

    assert c.callCode(
        'SELECT count(*) AS "count" FROM data WHERE x <= ${max}',
        {'data': pack(table), 'max': pack(2)}
    ) == {'errors': None, 'output': pack(pandas.DataFrame({'count': [2]}))}

    assert c.callCode(
        'SELECT count(*) AS "count" FROM data WHERE x IN ${set}',
        {'data': pack(table), 'set': pack([2, 3, 4])}
    ) == {'errors': None, 'output': pack(pandas.DataFrame({'count': [3]}))}
