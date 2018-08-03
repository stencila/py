from collections import OrderedDict
import json
import math

import pytest
import pandas
import matplotlib.pyplot as plt

from stencila.value import type, pack, unpack


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
        pack(lambda x: x)


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
