import tempfile
import os
import re

import pytest

from stencila import instance, Component

from marks import slow


def test_new():
    c = Component()
    assert isinstance(c, Component)
    assert c in instance.components
    assert instance.provide(c.address) is c
    assert re.match('^mem://[a-z0-9]+$', c.address)
    assert repr(c) == 'Component(%s)' % c.address


def test_del():
    l1 = len(instance.components)
    c = Component()
    l2 = len(instance.components)
    c.__del__()
    l3 = len(instance.components)

    assert l2 == l1+1
    assert l3 == l2-1


def test_read_write():
    p1 = tempfile.mkstemp()[1]
    p2 = tempfile.mkstemp()[1]

    c = Component(p1)
    assert c.path == p1

    c.read()
    assert c.path == p1

    c.read(p2)
    assert c.path == p2

    c.write()
    assert c.path == p2

    c.write(p1)
    assert c.path == p1


def test_read_nonexistant():
    c = Component()
    with pytest.raises(Exception) as exc:
        c.read('./foo/bar')
    assert 'Filesystem path does not exist' in str(exc.value)


def test_write_nonexistant():
    c = Component()
    dir = os.path.join(tempfile.mkdtemp(), 'foo')

    file = os.path.join(dir, 'bar', 'boop.txt')
    c.write(file)
    assert os.path.exists(os.path.join(dir, 'bar')), 'intentionally write directory'
    assert not os.path.exists(file), 'dont write file, that is for the derived class to do'
    assert c.path == file

    subdir = os.path.join(dir, 'bee')
    c.write(subdir)
    assert os.path.exists(subdir)
    assert c.path == subdir


def test_resolve():
    assert instance.resolve('~aaaaaaaa') == 'mem://aaaaaaaa'
    assert instance.resolve('./report.docx') == 'file://' + os.getcwd() + '/report.docx'
    assert instance.resolve('gh/foo/bar/report.md') == 'git://github.com/foo/bar/report.md'
    assert instance.resolve('stats/t-test') == 'git://stenci.la/stats/t-test'


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


def test_open():
    d = instance.open('gh/octocat/Spoon-Knife/README.md')
    assert d.type == 'document'
    assert d.address == 'git://github.com/octocat/Spoon-Knife/README.md'
