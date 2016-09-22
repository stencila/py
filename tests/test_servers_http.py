import re

from stencila import instance, Session
from stencila.servers.http import HttpServer

from werkzeug.wrappers import Request, Response
from werkzeug.test import Client, EnvironBuilder


def request(**kwargs):
    return Request(EnvironBuilder(**kwargs).get_environ())


def test_serve():
    s = HttpServer(instance)
    c = Client(s, Response)

    assert s.serve() == s.origin

    r = c.get('/')
    assert r.status == '200 OK'
    assert not re.search('components', r.data.decode('utf-8')), 'is not authenticated'

    r = c.get('/?token='+instance.token)
    assert r.status == '200 OK'
    assert re.search('components', r.data.decode('utf-8')), 'is authenticated'


def test_dispatch():
    s = HttpServer(None)

    assert s.dispatch('/web/some/file.js') == (s.web, ['some/file.js'])
    assert s.dispatch('/favicon.ico') == (s.web, ['images/favicon.ico'])

    assert s.dispatch('/') == (s.page, [None])
    assert s.dispatch('/!manifest') == (s.call, [None, 'manifest'])


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
    assert r.data.decode('utf-8').splitlines()[0] == '<!DOCTYPE html>'


def test_call():
    s = HttpServer(instance)
    c = Session()

    r = s.call(request(
        method='PUT',
        data='{"expr":"6*7"}'
    ), c.address, 'show')
    assert r.status == '200 OK'
    assert r.data.decode('utf-8') == '"42"'
