from stencila.python_context import PythonContext
from stencila.value import pack


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
