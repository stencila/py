from stencila.python_context import PythonContext
from stencila.value import pack

import matplotlib.pyplot as plt


def test_new():
    s = PythonContext()

    assert isinstance(s, PythonContext)


def test_executeCode():
    s = PythonContext()

    assert s.executeCode('') == {'messages': [], 'value': None, 'output': None}

    assert s.executeCode('x = 42') == {'messages': [], 'value': None, 'output': None}

    assert s.executeCode('x') == {'messages': [], 'value': pack(42), 'output': None}

    err = s.executeCode('foo')['messages'][0]
    assert err['line'] == 1
    assert err['message'] == "NameError: name 'foo' is not defined"

    err = s.executeCode('y = 24\nfoo')['messages'][0]
    assert err['line'] == 2
    assert err['message'] == "NameError: name 'foo' is not defined"

    value = s.executeCode('plt.plot(range(5))')['value']
    assert value['type'] == 'image'
    assert value['src'][:10] == 'data:image'

    result = s.executeCode('foo')
    value = result['value']
    assert value is None
    error = result['messages'][0]
    assert error['line'] == 1
    assert "name 'foo' is not defined" in error['message']

    result = s.executeCode('a syntax error')
    value = result['value']
    assert value is None
    error = result['messages'][0]
    assert error['line'] == 0
    assert error['message'][:-19] == "SyntaxError: invalid syntax"
