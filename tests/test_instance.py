import os
import re
import tempfile

from stencila import instance, Instance, Document

import pytest
from marks import slow

def test_instance():
    assert isinstance(instance, Instance)

@pytest.mark.skip
def test_config():
    os.environ['STENCILA_STARTUP_SERVE'] = 'false'
    instance = Instance()
    assert instance._config['startup']['serve'] is False


def test_lengthen():
    assert Instance.lengthen('new://document') == 'new://document'
    assert Instance.lengthen('ftp://foo/bar') == 'ftp://foo/bar'

    assert Instance.lengthen('+document') == 'new://document'
    assert Instance.lengthen('~aaaaaaaa') == 'id://aaaaaaaa'
    assert Instance.lengthen('./report.docx') == 'file://' + os.getcwd() + '/report.docx'
    assert Instance.lengthen('https://foo.com/report.md') == 'https://foo.com/report.md'
    assert Instance.lengthen('bb/foo/bar/report.md') == 'git://bitbucket.org/foo/bar/report.md'
    assert Instance.lengthen('gh/foo/bar/report.md') == 'git://github.com/foo/bar/report.md'
    assert Instance.lengthen('gl/foo/bar/report.md') == 'git://gitlab.com/foo/bar/report.md'
    assert Instance.lengthen('stats/t-test') == 'git://stenci.la/stats/t-test'


def test_shorten():
    assert Instance.shorten('new://document') == '+document'
    assert Instance.shorten('id://aaaaaaaa') == '~aaaaaaaa'
    assert Instance.shorten('file://' + os.getcwd() + '/report.docx') == os.getcwd() + '/report.docx'
    assert Instance.shorten('https://foo.com/report.md') == 'https://foo.com/report.md'
    assert Instance.shorten('git://bitbucket.org/foo/bar/report.md') == 'bb/foo/bar/report.md'
    assert Instance.shorten('git://github.com/foo/bar/report.md') == 'gh/foo/bar/report.md'
    assert Instance.shorten('git://gitlab.com/foo/bar/report.md') == 'gl/foo/bar/report.md'
    assert Instance.shorten('git://stenci.la/stats/t-test') == 'stats/t-test'


def test_lengthen_shorten():
    def ls(address):
        return Instance.shorten(Instance.lengthen(address))

    assert ls('+document') == '+document'
    assert ls('new://document') == '+document'
    assert ls('~aaaaaaaa') == '~aaaaaaaa'
    assert ls('id://aaaaaaaa') == '~aaaaaaaa'
    assert ls('gh/foo/bar/report.md') == 'gh/foo/bar/report.md'
    assert ls('gh/foo/bar/report.md@1.1.0') == 'gh/foo/bar/report.md@1.1.0'


def test_split():
    assert Instance.split('+document') == ('new', 'document', None)
    assert Instance.split('~aaaaaaaa') == ('id', 'aaaaaaaa', None)

    assert Instance.split('stats/t-test') == ('git', 'stenci.la/stats/t-test', None)
    assert Instance.split('stats/t-test@1.1.0') == ('git', 'stenci.la/stats/t-test', '1.1.0')


@pytest.mark.skip
def test_know():
    assert Instance.know('+document') == 'yes'
    assert Instance.know('~aaaaaaaa') == 'yes'

    assert Instance.know('./foo/bar.Rmd') == 'yes'

    assert Instance.know('./foo/bar') == 'maybe'

    assert Instance.know('gopher://foo/bar') == 'no'


def test_clone_new():
    assert instance.clone('new://document') is None


def test_clone_mem():
    assert instance.clone('mem://aaaaaaaa') is None


def test_clone_file():
    with tempfile.NamedTemporaryFile() as file:
        assert instance.clone('file://' + file.name) == file.name

    with pytest.raises(Exception) as exc:
        instance.clone('file://foo/bar')
    assert 'Local file system path does not exist' in str(exc.value)


@slow
def test_clone_http():
    assert re.match(r'^/tmp/\w+\.html$', instance.clone('http://docs.python.org/2/library/intro.html'))
    assert re.match(r'^/tmp/\w+\.json$', instance.clone('https://httpbin.org/get'))


@slow
def test_clone_git():
    assert instance.clone('gh/octocat/Spoon-Knife/README.md@bb4cc8d') == \
        os.path.join(instance.home, 'github.com/octocat/Spoon-Knife/bb4cc8d/README.md')

    assert instance.clone('gh/octocat/Spoon-Knife/README.md') == \
        os.path.join(instance.home, 'github.com/octocat/Spoon-Knife/master/README.md')

    assert instance.clone('gh/octocat/Spoon-Knife/index.html@master') == \
        os.path.join(instance.home, 'github.com/octocat/Spoon-Knife/master/index.html')


def test_open_new():
    d = instance.open('+document')
    assert d.type == 'document'
    assert re.match(r'^id://', d.address)


def test_open_mem():
    d1 = Document()
    d2 = instance.open(d1.address)
    assert d2 is d1


@slow
def test_open_http():
    d = instance.open('https://raw.githubusercontent.com/octocat/Spoon-Knife/master/README.md')
    assert d.type == 'document'
    assert d.address == 'https://raw.githubusercontent.com/octocat/Spoon-Knife/master/README.md'


@slow
def test_open():
    d = instance.open('gh/octocat/Spoon-Knife/README.md')
    assert d.type == 'document'
    assert d.address == 'git://github.com/octocat/Spoon-Knife/README.md'


def test_url():
    instance.serve(real=False)
    assert re.match(r'http://127\.0\.0\.1:2\d\d\d', instance.url())

    d = instance.open('+document')
    assert instance.url(d) == instance.url() + '/' + instance.shorten(d.address)


def test_serve():
    assert instance.serve(real=False) == instance.url()
