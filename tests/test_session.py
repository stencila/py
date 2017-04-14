from stencila import host, PySession

import pytest


@pytest.mark.skip
def test_new():
    s = PySession()

    assert isinstance(s, PySession)
    assert s in host.components


@pytest.mark.skip
def test_execute():
    s = PySession()

    assert s.execute('x = 42')['errors'] is None

    err = s.execute('x = 42\nfoo')['errors']
    assert err['error'] == 'NameError'
    assert err['message'] == "name 'foo' is not defined"
    assert err['line'] == 2
    assert err['trace'] == [['code', 2, '', '']]


@pytest.mark.skip
def test_print():
    s = PySession()

    assert s.print_('42') == '42'
    assert s.print_('6*7') == '42'
    assert s.print_('"Hello " + "world"') == 'Hello world'

    err = s.print_('foo')
    assert err['error'] == 'NameError'


@pytest.mark.skip
def test_run():
    s = PySession()
    s.run('a = 1')
    s.run('b = 2.0')
    s.run('c = "yo"')

    assert len(s.history) == 3
    assert s.objects() == {'a': 'int', 'b': 'float', 'c': 'str'}
