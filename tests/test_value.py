from collections import OrderedDict
import json
import os
import math

import pytest
import pandas
import matplotlib.pyplot as plt

from stencila.value import type, pack, pack_function, unpack


def test_type():
    assert type(None) == 'null'

    assert type(True) == 'boolean'
    assert type(False) == 'boolean'

    assert type(42) == 'integer'
    assert type(1000000000) == 'integer'

    assert type(3.14) == 'number'
    assert type(1.1e-20) == 'number'

    assert type('') == 'string'
    assert type('Yo!') == 'string'

    assert type(list()) == 'array'
    assert type([1, 2, 3]) == 'array'
    assert type(tuple()) == 'array'
    assert type((1, 2, 3)) == 'array'

    assert type(dict()) == 'object'
    assert type(dict(a=1, b=2)) == 'object'

    assert type(plt.plot(range(5))) == 'matplotlib'

    assert type(dict(type='html', content='<img>')) == 'html'
    assert type(dict(type='image', content='')) == 'image'
    assert type(dict(type=1)) == 'object'


def check(obj, type, format, data=None):
    p = pack(obj)
    assert p['type'] == type
    assert p['format'] == format
    if data:
        assert p['data'] == json.loads(data)


def test_pack_primitive_types():
    check(None, 'null', 'json', 'null')

    check(True, 'boolean', 'json', 'true')
    check(False, 'boolean', 'json', 'false')

    check(42, 'integer', 'json', '42')
    check(1000000000, 'integer', 'json', '1000000000')

    check(3.14, 'number', 'json', '3.14')
    check(math.pi, 'number', 'json', '3.141592653589793')

    check(1.1e20, 'number', 'json', '1.1e+20')
    check(1.1e-20, 'number', 'json', '1.1e-20')

    check('', 'string', 'json', '""')
    check('Yo!', 'string', 'json', '"Yo!"')


def test_pack_errors_for_unhandled_types():
    with pytest.raises(Exception):
        pack(set())


def test_pack_works_for_dicts():
    check({}, 'object', 'json', '{}')
    check({
        'a': 1, 'b': 3.14, 'c': 'foo', 'd': {'e': 1, 'f': 2}
    }, 'object', 'json')


def test_pack_works_for_lists():
    check([], 'array', 'json', '[]')
    check([1, 2, 3, 4], 'array', 'json', '[1,2,3,4]')
    check([1.1, 2.1], 'array', 'json', '[1.1,2.1]')


def test_pack_works_for_a_data_frame():
    check(
        pandas.DataFrame(),
        'table', 'json',
        '{"type": "table", "data": {}}'
    )
    check(
        pandas.DataFrame({'a': [1, 2, 3]}),
        'table', 'json',
        '{"type": "table", "data": {"a": [1, 2, 3]}}'
    )
    check(
        pandas.DataFrame({'a': [True, False, True], 'b': ['xx', 'yy', 'zz']}),
        'table', 'json',
        '{"type": "table", "data": {"a": [true, false, true], "b": ["xx", "yy", "zz"]}}'
    )


def test_pack_works_for_plots():
    check(
        pandas.DataFrame(),
        'table', 'json',
        '{"type": "table", "data": {}}'
    )
    check(
        pandas.DataFrame({'a': [1, 2, 3]}),
        'table', 'json',
        '{"type": "table", "data": {"a": [1, 2, 3]}}'
    )
    check(
        pandas.DataFrame({'a': [True, False, True], 'b': ['xx', 'yy', 'zz']}),
        'table', 'json',
        '{"type": "table", "data": {"a": [true, false, true], "b": ["xx", "yy", "zz"]}}'
    )


def test_pack_function():
    # Test general interface

    # .. can be called with a string
    pkg = pack_function('def hello(who="world"): return "Hello"')
    assert pkg == {
        'type': 'function',
        'format': 'json',
        'data': {
            'name': 'hello',
            'methods': {
                'hello': {
                    'params': [{
                        'name': 'who',
                        'default': {'type': 'string', 'data': 'world'}
                    }]
                }
            }
        }
    }

    # ...or a function object
    def hello(who="world"): return "Hello"
    assert pack_function(hello) == pkg

    # ...or a file
    path = os.path.join(os.path.dirname(__file__), 'fixtures', 'funcs', 'hello.py')
    assert pack_function(file=path) == pkg

    # ...or a directory
    #path = os.path.join(os.path.dirname(__file__), 'fixtures', 'funcs')
    #count = pack_function(dir=path)
    #assert count == 2

    # FIXME: currently skipping the remaining tests!
    return

    # Test handling of errors in function source

    messages = context.compile({
        'type': 'cell',
        'code': 'def syntax_err:'
    })['messages']
    assert len(messages) == 1
    assert messages[0]['message'] == 'invalid syntax (<string>, line 1)'

    messages = context.compile({
        'type': 'cell',
        'code': 'def bad_pars(*x, *y): pass'
    })['messages']
    assert len(messages) == 1
    assert messages[0]['message'] == 'invalid syntax (<string>, line 1)'

    # Test parsing of parameters from source code only

    assert pack_function('def no_arg(): pass')[0]['params'] == []

    assert pack_function('def one_arg(x): pass')[0]['params'] == [{
        'name': 'x'
    }]

    assert pack_function('def defaults(x=42, y=None): pass')[0]['params'] == [{
        'name': 'x',
        'default': {
            'type': 'integer',
            'data': 42
        }
    }, {
        'name': 'y',
        'default': {
            'type': 'null',
            'data': None
        }
    }]

    assert pack_function('def two_args(x, y): pass')[0]['params'] == [{
        'name': 'x'
    }, {
        'name': 'y'
    }]

    assert pack_function('def arg_repeats(*x): pass')[0]['params'] == [{
        'name': 'x',
        'repeat': True
    }]

    assert pack_function('def arg_repeats(*x, **y): pass')[0]['params'] == [{
        'name': 'x',
        'repeat': True
    }, {
        'name': 'y',
        'extend': True
    }]

    # Test parsing of docstring
    func = pack_function('''
def func(x, y):
    """Summary

    Description of function

    Args:
        x (integer) : A Google style parameter spec

    Returns
    -------
    string
        A NumPy style return spec

    """
    pass
''')[0]
    assert func['summary'] == 'Summary'
    assert func['description'] == 'Description of function'
    assert func['params'] == [{
        'name': 'x',
        'description': 'A Google style parameter spec',
        'type': 'integer'
    }, {
        'name': 'y'
    }]
    assert func['returns'] == {
        'description': 'A NumPy style return spec',
        'type': 'string'
    }


def test_unpack_can_take_a_list_or_a_JSON_string():
    assert unpack('{"type":"null","format":"text","data":"null"}') is None
    assert unpack({'type': 'null', 'format': 'text', 'data': 'null'}) is None


def test_unpack_errors_if_package_is_malformed():
    with pytest.raises(Exception):
        unpack(1), 'should be a list'

    with pytest.raises(Exception):
        unpack({}), 'should have fields `type`, `format`, `data`'
    with pytest.raises(Exception):
        unpack('{}')
    with pytest.raises(Exception):
        unpack({'type': 'null'})
    with pytest.raises(Exception):
        unpack({'type': 'null', 'format': 'text'})

    with pytest.raises(Exception):
        unpack({'type': 'foo', 'format': 'foo', 'data': 'bar'})


def test_unpack_works_for_primitive_types():
    assert unpack({'type': 'null', 'format': 'text', 'data': 'null'}) is None

    assert unpack({'type': 'boolean', 'format': 'text', 'data': 'true'}) is True
    assert unpack({'type': 'boolean', 'format': 'text', 'data': 'false'}) is False

    assert unpack({'type': 'integer', 'format': 'text', 'data': '42'}) == 42
    assert unpack({'type': 'integer', 'format': 'text', 'data': '1000000000'}) == 1000000000

    assert unpack({'type': 'number', 'format': 'text', 'data': '3.12'}) == 3.12
    assert unpack({'type': 'number', 'format': 'text', 'data': '1e20'}) == 1e20

    assert unpack({'type': 'string', 'format': 'text', 'data': 'Yo!'}) == 'Yo!'


def test_unpack_works_for_objects():
    assert unpack({'type': 'object', 'format': 'json', 'data': '{}'}) == {}
    assert unpack(
        {'type': 'object', 'format': 'json', 'data': '{"a":1,"b":"foo","c":[1,2,3]}'}
    ) == {'a': 1, 'b': 'foo', 'c': [1, 2, 3]}


def test_unpack_works_for_arrays():
    assert unpack({'type': 'array', 'format': 'json', 'data': '[]'}) == []
    assert unpack({'type': 'array', 'format': 'json', 'data': '[1,2,3,4,5]'}) == [1, 2, 3, 4, 5]


def test_unpack_works_for_tabular_data():
    data = pandas.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})

    assert unpack({'type': 'table', 'format': 'json', 'data': {
        "type": "table",
        "data": OrderedDict((
            ("a", [1, 2, 3]),
            ("b", ["x", "y", "z"])
        ))
    }}).to_csv() == data.to_csv()
    assert unpack({'type': 'table', 'format': 'csv', 'data': 'a,b\n1,x\n2,y\n3,z'}).to_csv() == data.to_csv()
    assert unpack({'type': 'table', 'format': 'tsv', 'data': 'a\tb\n1\tx\n2\ty\n3\tz'}).to_csv() == data.to_csv()

    with pytest.raises(Exception):
        unpack({'type': 'table', 'format': 'foo', 'data': 'bar'})
