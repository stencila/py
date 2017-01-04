import math

import pytest
import pandas

from stencila.packing import pack, unpack


def check(obj, type, format, value=None):
    p = pack(obj)
    assert p['type'] == type
    assert p['format'] == format
    if value:
        assert p['value'] == value


def test_primitive_types():
    check(None, 'null', 'text', 'null')

    check(True, 'bool', 'text', 'true')
    check(False, 'bool', 'text', 'false')

    check(42, 'int', 'text', '42')
    check(1000000000, 'int', 'text', '1000000000')

    check(3.14, 'flt', 'text', '3.14')
    check(math.pi, 'flt', 'text', '3.141592653589793')

    check(1.1e20, 'flt', 'text', '1.1e+20')
    check(1.1e-20, 'flt', 'text', '1.1e-20')

    check('', 'str', 'text', '')
    check('Yo!', 'str', 'text', 'Yo!')


def test_pack_errors_for_unhandled_types():
    with pytest.raises(Exception):
        pack(lambda x: x)


def test_pack_works_for_dicts():
    check({}, 'obj', 'json', '{}')
    check({
        'a': 1, 'b': 3.14, 'c': 'foo', 'd': {'e': 1, 'f': 2}
    }, 'obj', 'json')


def test_pack_works_for_lists():
    check([], 'arr', 'json', '[]')
    check([1, 2, 3, 4], 'arr', 'json', '[1,2,3,4]')
    check([1.1, 2.1], 'arr', 'json', '[1.1,2.1]')


def test_pack_works_for_a_data_frame():
    check(pandas.DataFrame(), 'tab', 'csv', '\n')
    check(pandas.DataFrame({'a': [1, 2, 3]}), 'tab', 'csv', 'a\n1\n2\n3\n')
    check(pandas.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']}), 'tab', 'csv', 'a,b\n1,x\n2,y\n3,z\n')


def test_unpack_can_take_a_list_or_a_JSON_string():
    assert unpack('{"type":"null","format":"text","value":"null"}') is None
    assert unpack({'type': 'null', 'format': 'text', 'value': 'null'}) is None


def test_unpack_errors_if_package_is_malformed():
    with pytest.raises(Exception):
        unpack(1), 'should be a list'

    with pytest.raises(Exception):
        unpack({}), 'should have fields `type`, `format`, `value`'
    with pytest.raises(Exception):
        unpack('{}')
    with pytest.raises(Exception):
        unpack({'type': 'null'})
    with pytest.raises(Exception):
        unpack({'type': 'null', 'format': 'text'})

    with pytest.raises(Exception):
        unpack({'type': 'foo', 'format': 'foo', 'value': 'bar'})


def test_unpack_works_for_primitive_types():
    assert unpack({'type': 'null', 'format': 'text', 'value': 'null'}) is None

    assert unpack({'type': 'bool', 'format': 'text', 'value': 'true'}) is True
    assert unpack({'type': 'bool', 'format': 'text', 'value': 'false'}) is False

    assert unpack({'type': 'int', 'format': 'text', 'value': '42'}) == 42
    assert unpack({'type': 'int', 'format': 'text', 'value': '1000000000'}) == 1000000000

    assert unpack({'type': 'flt', 'format': 'text', 'value': '3.12'}) == 3.12
    assert unpack({'type': 'flt', 'format': 'text', 'value': '1e20'}) == 1e20

    assert unpack({'type': 'str', 'format': 'text', 'value': 'Yo!'}) == 'Yo!'


def test_unpack_works_for_objects():
    assert unpack({'type': 'obj', 'format': 'json', 'value': '{}'}) == {}
    assert unpack(
        {'type': 'obj', 'format': 'json', 'value': '{"a":1,"b":"foo","c":[1,2,3]}'}
    ) == {'a': 1, 'b': 'foo', 'c': [1, 2, 3]}


def test_unpack_works_for_arrays():
    assert unpack({'type': 'arr', 'format': 'json', 'value': '[]'}) == []
    assert unpack({'type': 'arr', 'format': 'json', 'value': '[1,2,3,4,5]'}) == [1, 2, 3, 4, 5]


def test_unpack_works_for_tabular_data():
    result = pandas.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']}).to_csv()
    assert unpack({'type': 'tab', 'format': 'csv', 'value': 'a,b\n1,x\n2,y\n3,z'}).to_csv() == result
    assert unpack({'type': 'tab', 'format': 'tsv', 'value': 'a\tb\n1\tx\n2\ty\n3\tz'}).to_csv() == result

    with pytest.raises(Exception):
        unpack({'type': 'tab', 'format': 'foo', 'value': 'bar'})
