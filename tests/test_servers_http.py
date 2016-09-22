import re

from stencila import instance, Session
from stencila.servers.http import HttpServer

from werkzeug.wrappers import Request, Response
from werkzeug.test import EnvironBuilder


def request(**kwargs):
    return Request(EnvironBuilder(**kwargs).get_environ())


def test_http():
    s = HttpServer(instance)
    assert s.serve(real=False) == 'http://127.0.0.1:2000'


def test_dispatch():
    s = HttpServer(None)

    assert s.dispatch('/') == (s.home, [])
    assert s.dispatch('/manifest') == (s.manifest, [])

    assert s.dispatch('/favicon.ico') == (s.favicon, [])
    assert s.dispatch('/web/some/file.js') == (s.web, ['some/file.js'])

    assert s.dispatch('/mem://some/address') == (s.page, ['mem://some/address'])
    assert s.dispatch('/file://some/address') == (s.page, ['file://some/address'])

    assert s.dispatch('/mem://some/address!method') == (s.call, ['mem://some/address', 'method'])


def test_page():
    s = HttpServer(instance)
    c = Session()

    r = s.page(request(
        method='GET'
    ), c.address)
    assert r.status == '200 OK'
    assert re.match(r'^<!DOCTYPE', r.data)


def test_call():
    s = HttpServer(instance)
    c = Session()

    r = s.call(request(
        method='PUT',
        data='{"expr":"6*7"}'
    ), c.address, 'text')
    assert r.status == '200 OK'
    assert r.data == '42'
