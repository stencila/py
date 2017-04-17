from stencila.host import Host
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


def test_host_post():
    h = Host()

    id1 = h.post('PythonContext')
    id2 = h.post('PythonContext')
    assert id1 != id2

    with pytest.raises(Exception) as exc:
        h.post('fooType')
    exc.match('Unknown type: fooType')


# def test_host_get():
#     h = Host()

#     id = h.post('RContext')
#     assert inherits(h.get(id), 'RContext')

#     expect_error(h.get('foo'), 'Unknown instance')


# def test_host_put():
#     h = Host()

#     id = h.post('RContext')
#     assert h.put(id, 'runCode', list(code='6*7'))['output'], pack(42)
#     expect_error(h.put(id, 'fooBar'), 'Unknown method')
#     expect_error(h.put('foo', 'bar'), 'Unknown instance')


# def test_host_delete():
#     h = Host()

#     id = h.post('RContext')
#     assert inherits(h.get(id), 'RContext')
#     h.delete(id)
#     expect_error(h.delete(id), 'Unknown instance')


# def test_host_start_stop():
#     h = Host()

#     h.start()
#     assert h.servers, 'http'
#     assert length(h.servers), 1
#     assert length(h.options()['urls']), 1
#     h.stop()
#     assert length(h.servers), 0
#     assert length(h.options()['urls']), 0
