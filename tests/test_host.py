import json
import os
import platform
import tempfile

from stencila.host import Host
from stencila.python_context import PythonContext
from stencila.value import pack
from stencila.version import __version__

import pytest


def test_host():
    h = Host()

    assert isinstance(h, Host)


def test_user_dir():
    h = Host()
    if platform.system().lower() == 'linux' and os.getenv("HOME"):
        assert h.user_dir() == os.path.join(os.getenv("HOME"), '.stencila')


def test_temp_dir():
    h = Host()
    assert h.temp_dir() == os.path.join(tempfile.gettempdir(), 'stencila')


def test_host_manifest():
    h = Host()

    manifest = h.manifest()
    assert manifest['stencila']['package'] == 'py'
    assert manifest['stencila']['version'] == __version__
    assert manifest['types']['PythonContext'] == PythonContext.spec

    h.start()
    manifest = h.manifest()
    assert manifest['id'] == h.id
    assert manifest['process']['pid'] == os.getpid()
    assert len(manifest['instances']) == 0

    h.stop()


def test_host_register():
    h = Host()

    h.register()
    manifest = h.manifest()

    with open(os.path.join(h.user_dir(), 'hosts', 'py.json')) as manifest_file:
        assert manifest == json.load(manifest_file)


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
    result = h.put(id, 'execute', {'code': '6*7'})
    assert result['outputs'][0]['value']['data'] == 42

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
    assert len(h.manifest()['servers']) == 1
    h.stop()
    assert len(h.servers) == 0
    assert len(h.manifest()['servers']) == 0


def test_generate_token_authorize_token():
    host = Host()

    token1 = host.generate_token()
    host.authorize_token(token1)

    token2 = host.generate_token()
    host.authorize_token(token2)

    assert token1 != token2

    with pytest.raises(Exception) as exc:
        host.authorize_token("not a valid token")
    exc.match('Not enough segments')

    with pytest.raises(Exception) as exc:
        host.authorize_token("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1MjY5NjA1Nzl9.pgTAtdDGHZZd05hg-Tmy8Cl_yrWBzBSZMaCTkbztc1E")
    exc.match('Signature verification failed')
