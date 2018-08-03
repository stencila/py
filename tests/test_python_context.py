import os

from stencila.python_context import PythonContext
from stencila.value import pack


def test_new():
    context = PythonContext()

    assert isinstance(context, PythonContext)


def test_compile():
    context = PythonContext()

    assert context.compile('') == {
        'code': '',
        'expr': False,
        'global': False,
        'inputs': [],
        'lang': 'py',
        'messages': [],
        'options': {},
        'outputs': []
    }

    # Check inputs
    def check_inputs(code, inputs):
        cell = context.compile(code)
        assert cell['messages'] == []
        assert cell['inputs'] == inputs

    check_inputs('x', [{'name': 'x'}])
    check_inputs('x * y', [{'name': 'x'}, {'name': 'y'}])

    check_inputs('x = 1', [])
    check_inputs('x = 1\nx', [])
    check_inputs('x = 1\nx * y', [{'name': 'y'}])

    check_inputs('x()', [{'name': 'x'}])
    check_inputs('def x(): pass\nx()', [])
    check_inputs('def x(y, z): pass\nx()', [])
    check_inputs('class x: pass\nx()', [])

    check_inputs('foo.bar', [{'name': 'foo'}])
    check_inputs('import foo\nfoo.bar', [])
    check_inputs('import foo as bar\nbar', [])
    check_inputs('from foo import bar\nbar', [])
    check_inputs('from foo import bar as baz\nbaz', [])

    check_inputs('global foo\nfoo', [])
    check_inputs('global foo, bar\nfoo * bar', [])

    # Check built-in functions are not treated as inputs
    check_inputs('print(42)', [])
    check_inputs('range(10)', [])

    # Check for loop variable is not treated as an input
    check_inputs('for i in range(10): print(i)', [])

    # Check outputs
    def check_outputs(code, outputs):
        cell = context.compile(code)
        assert cell['messages'] == []
        assert cell['outputs'] == outputs

    check_outputs('x', [])
    check_outputs('x()', [])
    check_outputs('x = 1', [{'name': 'x'}])

    # Check syntax errors
    assert context.compile('[1,2')['messages'] == [{
        'type': 'error',
        'message': 'unexpected EOF while parsing (<unknown>, line 1)',
        'line': 1,
        'column': 5
    }]


def skip_test_compile_func():
    context = PythonContext()

    # Test general interface

    assert context.list(types=['function']) == []

    # .. can be called with a function operation
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

    # ...or a string
    assert context.compile_func(
        'def hello(who="world"): return "Hello"'
    )[0] == operation

    # ...or a function object
    def hello(who="world"): return "Hello"
    assert context.compile_func(hello)[0] == operation
    assert context.list(types=['function']) == ['hello']

    # ...or a file
    path = os.path.join(os.path.dirname(__file__), 'fixtures', 'funcs', 'hello.py')
    operation, messages = context.compile_func(file=path)
    assert operation == {
        'type': 'func',
        'name': 'hello',
        'params': [],
        'source': 'def hello():\n    return "Hello from %s" % __file__\n'
    }

    # ...or a directory
    path = os.path.join(os.path.dirname(__file__), 'fixtures', 'funcs')
    count = context.compile_func(dir=path)
    assert count == 2
    assert context.list(types=['function']).sort() == ['goodbye', 'hello'].sort()

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


def test_execute():
    context = PythonContext()

    assert context.execute('') == {
        'code': '',
        'expr': False,
        'global': False,
        'inputs': [],
        'lang': 'py',
        'messages': [],
        'options': {},
        'outputs': []
    }

    # Works when leading or trailing whitespace
    assert context.execute(' 2*1')['outputs'][0]['value'] == {'data': 2, 'format': 'json', 'type': 'integer'}
    assert context.execute('\t2*2')['outputs'][0]['value'] == {'data': 4, 'format': 'json', 'type': 'integer'}
    assert context.execute('\t2*3 \t')['outputs'][0]['value'] == {'data': 6, 'format': 'json', 'type': 'integer'}

    # Check outputs
    def check_outputs(code, inputs, outputs):
        cell = context.execute({
            'code': code,
            'inputs': inputs
        })
        assert cell['messages'] == []
        assert cell['outputs'] == outputs

    check_outputs('1.0', [], [{
        'value': {'type': 'number', 'format': 'json', 'data': 1}
    }])

    check_outputs('x = 3.1', [], [{
        'name':  'x',
        'value': {'type': 'number', 'format': 'json', 'data': 3.1}
    }])

    check_outputs('x * 2', [{
        'name': 'x',
        'value': {'type': 'number', 'format': 'json', 'data': 1.1}
    }], [{
        'value': {'type': 'number', 'format': 'json', 'data': 2.2}
    }])

    return

    assert context.execute('x = 42') == {'messages': [], 'value': None}

    assert context.execute('x') == {'messages': [], 'value': pack(42)}

    err = context.execute('foo')['messages'][0]
    assert err['line'] == 1
    assert err['message'] == "NameError: name 'foo' is not defined"

    err = context.execute('y = 24\nfoo')['messages'][0]
    assert err['line'] == 2
    assert err['message'] == "NameError: name 'foo' is not defined"

    value = context.execute('plt.plot(range(5))')['value']
    assert value['type'] == 'image'
    assert value['src'][:10] == 'data:image'

    result = context.execute('foo')
    value = result['value']
    assert value is None
    error = result['messages'][0]
    assert error['line'] == 1
    assert "name 'foo' is not defined" in error['message']

    result = context.execute('a syntax error')
    value = result['value']
    assert value is None
    error = result['messages'][0]
    assert error['line'] == 0
    assert error['message'][:-19] == "SyntaxError: invalid syntax"
