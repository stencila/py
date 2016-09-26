import os
import re
import tempfile

from stencila import instance, Instance, Document, Sheet, Session, Context

from marks import slow


def test_instance():
    assert isinstance(instance, Instance)


def test_config():
    os.environ['STENCILA_STARTUP_SERVE'] = 'false'
    instance = Instance()
    assert instance._config['startup']['serve'] == False


def test_resolve():
    assert instance.resolve('~aaaaaaaa') == 'mem://aaaaaaaa'
    assert instance.resolve('./report.docx') == 'file://' + os.getcwd() + '/report.docx'
    assert instance.resolve('https://foo.com/report.md') == 'https://foo.com/report.md'
    assert instance.resolve('bb/foo/bar/report.md') == 'git://bitbucket.org/foo/bar/report.md'
    assert instance.resolve('gh/foo/bar/report.md') == 'git://github.com/foo/bar/report.md'
    assert instance.resolve('gl/foo/bar/report.md') == 'git://gitlab.com/foo/bar/report.md'
    assert instance.resolve('stats/t-test') == 'git://stenci.la/stats/t-test'


def test_shorten():
    assert instance.shorten('mem://aaaaaaaa') == '~aaaaaaaa'
    assert instance.shorten('file://' + os.getcwd() + '/report.docx') == os.getcwd() + '/report.docx'
    assert instance.shorten('https://foo.com/report.md') == 'https://foo.com/report.md'
    assert instance.shorten('git://bitbucket.org/foo/bar/report.md') == 'bb/foo/bar/report.md'
    assert instance.shorten('git://github.com/foo/bar/report.md') == 'gh/foo/bar/report.md'
    assert instance.shorten('git://gitlab.com/foo/bar/report.md') == 'gl/foo/bar/report.md'
    assert instance.shorten('git://stenci.la/stats/t-test') == 'stats/t-test'


def test_obtain_mem():
    assert instance.obtain('mem://aaaaaaaa') is None


def test_obtain_file():
    h, p = tempfile.mkstemp()
    assert instance.obtain('file://' + p) == p


@slow
def test_obtain_http():
    assert re.match('/tmp/\w+\.html', instance.obtain('http://docs.python.org/2/library/intro.html'))
    assert re.match('/tmp/\w+\.json', instance.obtain('https://httpbin.org/get'))


@slow
def test_obtain_git():
    assert instance.obtain('git://github.com/octocat/Spoon-Knife/README.md', 'bb4cc8d') == \
        os.path.join(instance.home, 'github.com/octocat/Spoon-Knife/bb4cc8d/README.md')

    assert instance.obtain('git://github.com/octocat/Spoon-Knife/README.md') == \
        os.path.join(instance.home, 'github.com/octocat/Spoon-Knife/master/README.md')

    assert instance.obtain('git://github.com/octocat/Spoon-Knife/index.html', 'master') == \
        os.path.join(instance.home, 'github.com/octocat/Spoon-Knife/master/index.html')


def test_new():
    assert isinstance(instance.new('document'), Document)
    assert isinstance(instance.new('sheet'), Sheet)
    assert isinstance(instance.new('session'), Session)
    assert isinstance(instance.new('context'), Context)


def test_open():
    d = instance.open('gh/octocat/Spoon-Knife/README.md')
    assert d.type == 'document'
    assert d.address == 'git://github.com/octocat/Spoon-Knife/README.md'


def test_url():
    instance.serve(real=False)
    assert re.match(r'http://127\.0\.0\.1:2\d\d\d', instance.url())
    d = instance.new('document')
    assert instance.url(d) == instance.url() + '/' + instance.shorten(d.address)


def test_serve():
    assert instance.serve(real=False) == instance.url()
