import pandas
import pytest

from stencila.context import Context
from stencila.sqlite_context import SqliteContext
from stencila.host import Host


def test_new():
    c = SqliteContext()

    assert isinstance(c, SqliteContext)


def test_execute():
    c = SqliteContext()

    assert c.execute('') == {'messages': [], 'value': None}

    assert c.execute('SELECT 42 AS x') == {'messages': [], 'value': Context.pack(pandas.DataFrame([{'x': 42}]))}

    err = c.execute('foo')['messages'][0]
    assert err['line'] == 0
    assert err['message'] == 'near "foo": syntax error'

    err = c.execute('SELECT col FROM foo')['messages'][0]
    assert err['line'] == 0
    assert err['message'] == 'no such table: foo'


def test_pack():
    host = Host()
    host.start()

    c = SqliteContext(host=host, name='sqliteContext1')
    result = c.execute(TEST_TABLES_SQL)
    assert result == {'messages': [], 'value': None}

    # Pack to a package
    package = c.pack('test_table_1', max_rows=256)
    x = package['data']['data']['x']
    assert len(x['values']) == 256
    assert x['values'][:3] == ['a', 'a', 'a']

    # Force packing to a pointer
    pointer = c.pack('test_table_1', max_rows=0)
    assert pointer['type'] == 'table'
    assert pointer['host']['url'] == host.servers['http']['url']
    assert pointer['context'] == 'sqliteContext1'
    assert pointer['name'] == 'test_table_1'

    host.stop()


def test_fetch():
    host = Host()
    host.start()

    context = SqliteContext(host=host, name='sqliteContext1')
    result = context.execute(TEST_TABLES_SQL)
    assert result == {'messages': [], 'value': None}

    # Fetch a variable from context
    package = context.fetch('test_table_1')
    x = package['data']['data']['x']
    assert len(x['values']) == 256
    assert x['values'][:3] == ['a', 'a', 'a']

    host.stop()


@pytest.mark.skip(reason="wip on refactoring context API")
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


TEST_TABLES_SQL = '''
    CREATE TABLE test_table_1 (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      x TEXT NOT NULL,
      y INT NOT NULL
    );
    INSERT INTO test_table_1 (x,y)
    SELECT 'a', 42
    FROM (SELECT * FROM (
         (SELECT 0 UNION ALL SELECT 1) t2,
         (SELECT 0 UNION ALL SELECT 1) t4,
         (SELECT 0 UNION ALL SELECT 1) t8,
         (SELECT 0 UNION ALL SELECT 1) t16,
         (SELECT 0 UNION ALL SELECT 1) t32,
         (SELECT 0 UNION ALL SELECT 1) t64,
         (SELECT 0 UNION ALL SELECT 1) t128,
         (SELECT 0 UNION ALL SELECT 1) t256
         )
    );
'''
