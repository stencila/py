import re

from stencila import instance, PySession
from stencila.servers.http import HttpServer

from werkzeug.wrappers import Request, Response
from werkzeug.test import Client, EnvironBuilder

import pytest


def request(**kwargs):
    return Request(EnvironBuilder(**kwargs).get_environ())


@pytest.mark.skip
def stest_serve():
    s = HttpServer(instance)
    c = Client(s, Response)

    s.serve()
    assert s.status == 'on'
    assert re.match('^http://127.0.0.1', s.origin)

    r = c.get('/')
    assert r.status == '403 FORBIDDEN'
    assert not re.search('components', r.data.decode('utf-8')), 'is not authenticated'

    r = c.get('/?token='+instance.token)
    assert r.status == '200 OK'
    assert re.search('components', r.data.decode('utf-8')), 'is authenticated'

    r = c.get('/!foo-bar')
    assert r.status == '500 INTERNAL SERVER ERROR'
    assert re.search('Traceback', r.data.decode('utf-8')), 'returns a traceback of error'

    s.serve(False)
    assert s.status == 'off'


def test_route():
    s = HttpServer(None)

    assert s.route('GET', '/web/some/file.js') == (s.web, 'some/file.js')
    assert s.route('GET', '/favicon.ico') == (s.web, 'images/favicon.ico')

    assert s.route('GET', '/') == (s.show, None)
    assert s.route('GET', '/!manifest') == (s.get, None, 'manifest')

    assert s.route('GET', '/id://some/address') == (s.show, 'id://some/address')
    assert s.route('GET', '/file://some/address') == (s.show, 'file://some/address')

    assert s.route('POST', '/id://some/address!method') == (s.call, 'id://some/address', 'method')


def test_web():
    s = HttpServer(instance)

    r = s.web(request(method='GET'), 'some/file.js')
    assert r.status == '302 FOUND'
    assert 'Location' in r.headers


def test_get():
    s = HttpServer(instance)
    c = PySession()

    r = s.get(request(
        method='GET'
    ), c.address, 'type')
    assert r.status == '200 OK'
    assert r.data.decode('utf-8') == '"py-session"'


def test_call():
    s = HttpServer(instance)
    c = PySession()

    r = s.call(request(
        method='PUT',
        data='{"expr":"6*7"}'
    ), c.address, 'print')
    assert r.status == '200 OK'
    assert r.data.decode('utf-8') == '"42"'
