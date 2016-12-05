import os
import re
import tempfile

from stencila import host, Host, Document

import pytest
from marks import slow

def test_host():
    assert isinstance(host, Host)

@pytest.mark.skip
def test_config():
    os.environ['STENCILA_STARTUP_SERVE'] = 'false'
    host = Host()
    assert host._config['startup']['serve'] is False


def test_lengthen():
    assert Host.lengthen('new://document') == 'new://document'
    assert Host.lengthen('ftp://foo/bar') == 'ftp://foo/bar'

    assert Host.lengthen('+document') == 'new://document'
    assert Host.lengthen('~aaaaaaaa') == 'id://aaaaaaaa'
    assert Host.lengthen('./report.docx') == 'file://' + os.getcwd() + '/report.docx'
    assert Host.lengthen('https://foo.com/report.md') == 'https://foo.com/report.md'
    assert Host.lengthen('bb/foo/bar/report.md') == 'git://bitbucket.org/foo/bar/report.md'
    assert Host.lengthen('gh/foo/bar/report.md') == 'git://github.com/foo/bar/report.md'
    assert Host.lengthen('gl/foo/bar/report.md') == 'git://gitlab.com/foo/bar/report.md'
    assert Host.lengthen('stats/t-test') == 'git://stenci.la/stats/t-test'


def test_shorten():
    assert Host.shorten('new://document') == '+document'
    assert Host.shorten('id://aaaaaaaa') == '~aaaaaaaa'
    assert Host.shorten('file://' + os.getcwd() + '/report.docx') == os.getcwd() + '/report.docx'
    assert Host.shorten('https://foo.com/report.md') == 'https://foo.com/report.md'
    assert Host.shorten('git://bitbucket.org/foo/bar/report.md') == 'bb/foo/bar/report.md'
    assert Host.shorten('git://github.com/foo/bar/report.md') == 'gh/foo/bar/report.md'
    assert Host.shorten('git://gitlab.com/foo/bar/report.md') == 'gl/foo/bar/report.md'
    assert Host.shorten('git://stenci.la/stats/t-test') == 'stats/t-test'


def test_lengthen_shorten():
    def ls(address):
        return Host.shorten(Host.lengthen(address))

    assert ls('+document') == '+document'
    assert ls('new://document') == '+document'
    assert ls('~aaaaaaaa') == '~aaaaaaaa'
    assert ls('id://aaaaaaaa') == '~aaaaaaaa'
    assert ls('gh/foo/bar/report.md') == 'gh/foo/bar/report.md'
    assert ls('gh/foo/bar/report.md@1.1.0') == 'gh/foo/bar/report.md@1.1.0'


def test_split():
    assert Host.split('+document') == ('new', 'document', None)
    assert Host.split('~aaaaaaaa') == ('id', 'aaaaaaaa', None)

    assert Host.split('stats/t-test') == ('git', 'stenci.la/stats/t-test', None)
    assert Host.split('stats/t-test@1.1.0') == ('git', 'stenci.la/stats/t-test', '1.1.0')


@pytest.mark.skip
def test_know():
    assert Host.know('+document') == 'yes'
    assert Host.know('~aaaaaaaa') == 'yes'

    assert Host.know('./foo/bar.Rmd') == 'yes'

    assert Host.know('./foo/bar') == 'maybe'

    assert Host.know('gopher://foo/bar') == 'no'


def test_clone_new():
    assert host.clone('new://document') is None


def test_clone_mem():
    assert host.clone('mem://aaaaaaaa') is None


def test_clone_file():
    with tempfile.NamedTemporaryFile() as file:
        assert host.clone('file://' + file.name) == file.name

    with pytest.raises(Exception) as exc:
        host.clone('file://foo/bar')
    assert 'Local file system path does not exist' in str(exc.value)


@slow
def test_clone_http():
    assert re.match(r'^/tmp/\w+\.html$', host.clone('http://docs.python.org/2/library/intro.html'))
    assert re.match(r'^/tmp/\w+\.json$', host.clone('https://httpbin.org/get'))


@slow
def test_clone_git():
    assert host.clone('gh/octocat/Spoon-Knife/README.md@bb4cc8d') == \
        os.path.join(host.home, 'github.com/octocat/Spoon-Knife/bb4cc8d/README.md')

    assert host.clone('gh/octocat/Spoon-Knife/README.md') == \
        os.path.join(host.home, 'github.com/octocat/Spoon-Knife/master/README.md')

    assert host.clone('gh/octocat/Spoon-Knife/index.html@master') == \
        os.path.join(host.home, 'github.com/octocat/Spoon-Knife/master/index.html')


def test_open_new():
    d = host.open('+document')
    assert d.type == 'document'
    assert re.match(r'^id://', d.address)


def test_open_mem():
    d1 = Document()
    d2 = host.open(d1.address)
    assert d2 is d1


@slow
def test_open_http():
    d = host.open('https://raw.githubusercontent.com/octocat/Spoon-Knife/master/README.md')
    assert d.type == 'document'
    assert d.address == 'https://raw.githubusercontent.com/octocat/Spoon-Knife/master/README.md'


@slow
def test_open():
    d = host.open('gh/octocat/Spoon-Knife/README.md')
    assert d.type == 'document'
    assert d.address == 'git://github.com/octocat/Spoon-Knife/README.md'


def test_url():
    host.serve(real=False)
    assert re.match(r'http://127\.0\.0\.1:2\d\d\d', host.url())

    d = host.open('+document')
    assert host.url(d) == host.url() + '/' + host.shorten(d.address)


def test_serve():
    assert host.serve(real=False) == host.url()
