from stencila.python_context import PythonContext
from stencila.value import pack

import matplotlib.pyplot as plt


def test_new():
    s = PythonContext()

    assert isinstance(s, PythonContext)


def test_runCode():
    s = PythonContext()

    assert s.runCode('') == {'errors': None, 'output': None}

    assert s.runCode('x = 42') == {'errors': None, 'output': None}

    assert s.runCode('x') == {'errors': None, 'output': pack(42)}

    err = s.runCode('foo')['errors'][0]
    assert err['line'] == 1
    assert err['message'] == "NameError: name 'foo' is not defined"

    err = s.runCode('y = 24\nfoo')['errors'][0]
    assert err['line'] == 2
    assert err['message'] == "NameError: name 'foo' is not defined"

    output = s.runCode('plt.plot(range(5))')['output']
    assert output['type'] == 'image'
    assert output['format'] == 'png'
    assert output['content'][:10] == 'iVBORw0KGg'


def test_callCode():
    s = PythonContext()

    assert s.callCode('') == {'errors': None, 'output': pack(None)}

    assert s.callCode('return 42') == {'errors': None, 'output': pack(42)}

    assert s.callCode('return foo', {'foo': pack('bar')}) == {'errors': None, 'output': pack('bar')}

    result = s.callCode('return foo')
    output = result['output']
    assert output is None
    error = result['errors'][0]
    assert error['line'] == 2
    assert "name 'foo' is not defined" in error['message']

    result = s.callCode('a syntax error')
    output = result['output']
    assert output is None
    error = result['errors'][0]
    assert error['line'] == 0
    assert error['message'][:-19] == "SyntaxError: invalid syntax"
