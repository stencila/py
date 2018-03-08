from stencila.python_context import PythonContext
from stencila.value import pack


def test_new():
    s = PythonContext()

    assert isinstance(s, PythonContext)


def test_compile_func():
    context = PythonContext()

    # Test general interface

    operation, messages = context.compile_func({
        'type': 'func',
        'source': 'def hello(who="world"): return "Hello"'
    })
    assert messages == []
    assert operation == {
        'type': 'func',
        'source': 'def hello(who="world"): return "Hello"',
        'name': 'hello',
        'params': [{
            'name': 'who',
            'default': {'type': 'string', 'data': 'world'}
        }]
    }

    # Test handling of errors in function source

    assert context.compile({
        'type': 'func',
        'source': 'def syntax_err:'
    })['messages'] == [{
        'type': 'error',
        'message': 'invalid syntax (<string>, line 1)'
    }]

    assert context.compile({
        'type': 'func',
        'source': 'def bad_pars(*x, *y): pass'
    })['messages'] == [{
        'type': 'error',
        'message': 'invalid syntax (<string>, line 1)'
    }]

    # Test parsing of parameters from source code only

    assert context.compile_func('def no_arg(): pass')[0]['params'] == []

    assert context.compile_func('def one_arg(x): pass')[0]['params'] == [{
        'name': 'x'
    }]

    assert context.compile_func('def defaults(x=42, y=None): pass')[0]['params'] == [{
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

    assert context.compile_func('def two_args(x, y): pass')[0]['params'] == [{
        'name': 'x'
    }, {
        'name': 'y'
    }]

    assert context.compile_func('def arg_repeats(*x): pass')[0]['params'] == [{
        'name': 'x',
        'repeat': True
    }]

    assert context.compile_func('def arg_repeats(*x, **y): pass')[0]['params'] == [{
        'name': 'x',
        'repeat': True
    }, {
        'name': 'y',
        'extend': True
    }]

    # Test parsing of docstring
    func = context.compile_func('''
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
