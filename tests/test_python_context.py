from stencila.python_context import PythonContext
from stencila.value import pack


def test_new():
    s = PythonContext()

    assert isinstance(s, PythonContext)


def test_executeCode():
    s = PythonContext()

    assert s.execute('') == {'messages': [], 'value': None}

    assert s.execute('x = 42') == {'messages': [], 'value': None}

    assert s.execute('x') == {'messages': [], 'value': pack(42)}

    err = s.execute('foo')['messages'][0]
    assert err['line'] == 1
    assert err['message'] == "NameError: name 'foo' is not defined"

    err = s.execute('y = 24\nfoo')['messages'][0]
    assert err['line'] == 2
    assert err['message'] == "NameError: name 'foo' is not defined"

    value = s.execute('plt.plot(range(5))')['value']
    assert value['type'] == 'image'
    assert value['src'][:10] == 'data:image'

    result = s.execute('foo')
    value = result['value']
    assert value is None
    error = result['messages'][0]
    assert error['line'] == 1
    assert "name 'foo' is not defined" in error['message']

    result = s.execute('a syntax error')
    value = result['value']
    assert value is None
    error = result['messages'][0]
    assert error['line'] == 0
    assert error['message'][:-19] == "SyntaxError: invalid syntax"
