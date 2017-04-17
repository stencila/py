from stencila.host import Host
from stencila.python_context import PythonContext
from stencila.value import pack
from stencila.version import __version__

import pytest


def test_host():
    h = Host()

    assert isinstance(h, Host)


def test_host_options():
    h = Host()

    manifest = h.options()
    assert manifest['stencila']['package'] == 'py'
    assert manifest['stencila']['version'] == __version__
    assert manifest['types'][0] == 'PythonContext'
    assert len(manifest['instances']) == 0
    assert len(manifest['types']) > 0


def test_host_post():
    h = Host()

    id1 = h.post('PythonContext')
    id2 = h.post('PythonContext')
    assert id1 != id2

    with pytest.raises(Exception) as exc:
        h.post('fooType')
    exc.match('Unknown type: fooType')


def test_host_get():
    h = Host()

    id = h.post('PythonContext')
    assert isinstance(h.get(id), PythonContext)

    with pytest.raises(Exception) as exc:
        h.get('foo')
    exc.match('Unknown instance')


def test_host_put():
    h = Host()

    id = h.post('PythonContext')
    assert h.put(id, 'runCode', {'code': '6*7'})['output'], pack(42)

    with pytest.raises(Exception) as exc:
        h.put(id, 'fooBar')
    exc.match('Unknown method')

    with pytest.raises(Exception) as exc:
        h.put('foo', 'bar')
    exc.match('Unknown instance')


def test_host_delete():
    h = Host()

    id = h.post('PythonContext')
    assert isinstance(h.get(id), PythonContext)
    h.delete(id)
    with pytest.raises(Exception) as exc:
        h.delete(id)
    exc.match('Unknown instance')


def test_host_start_stop():
    h = Host()

    h.start()
    assert h.servers, 'http'
    assert len(h.servers) == 1
    assert len(h.options()['urls']) == 1
    h.stop()
    assert len(h.servers) == 0
    assert len(h.options()['urls']) == 0
