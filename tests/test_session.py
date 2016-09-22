from stencila import instance, Session


def test_new():
    s = Session()

    assert isinstance(s, Session)
    assert s in instance.components


def test_execute():
    s = Session()

    assert s.execute('x = 42') is None

    err = s.execute('x = 42\nfoo')
    assert err['error'] == 'NameError'
    assert err['message'] == "name 'foo' is not defined"
    assert err['line'] == 2
    assert err['trace'] == [['code', 2, '', '']]


def test_run():
    s = Session()
    s.run('a = 1')
    s.run('b = 2.0')
    s.run('c = "yo"')

    assert len(s.history) == 3
    assert s.objects() == {'a': 'int', 'b': 'float', 'c': 'str'}
