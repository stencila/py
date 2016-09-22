from stencila import instance, Session


def test_new():
    s = Session()

    assert isinstance(s, Session)
    assert s in instance.components


def test_execute():
    s = Session()

    assert s.execute('x = 42') is None

    err = s.execute('x = 42\nfoo')
    assert err['line'] == 2
    assert err['type'] == 'NameError'
    assert err['trace'] == [['code', 2, '', None]]

    assert len(s.history) == 2
    assert s.history[0] == {'input': 'x = 42', 'output': None}

def test_content():
    s = Session()
    s.execute('a = 1')
    s.execute('b = 2')

    assert s.objects() == {'a': 'int', 'b': 'int'}

    h = s.content()

    assert h == ''
