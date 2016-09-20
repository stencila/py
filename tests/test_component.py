import tempfile
import os
import re

import pytest

from stencila import Component, home, components, resolve, obtain

from marks import slow


def test_new():
    c = Component()
    assert isinstance(c, Component)
    assert c in components
    assert re.match('^mem://[a-z0-9]+$', c.address())


def test_del():
    l1 = len(components)
    c = Component()
    l2 = len(components)
    c.__del__()
    l3 = len(components)

    assert l2 == l1+1
    assert l3 == l2-1


def test_read_write():
    p1 = tempfile.mkstemp()[1]
    p2 = tempfile.mkstemp()[1]

    c = Component(p1)
    assert c.path() == p1

    c.read()
    assert c.path() == p1

    c.read(p2)
    assert c.path() == p2

    c.write()
    assert c.path() == p2

    c.write(p1)
    assert c.path() == p1


def test_read_error():
    c = Component('./foo/bar')  # This is OK

    with pytest.raises(Exception) as exc:
        c.read()  # This explicit read is not OK
    assert 'Filesystem path does not exist' in str(exc.value)


def test_write_nonexistant():
    dir = os.path.join(tempfile.mkdtemp(), 'foo')

    file = os.path.join(dir, 'bar', 'boop.txt')
    c = Component(file)
    assert c.path() == file
    c.write()
    assert os.path.exists(os.path.join(dir, 'bar'))
    assert not os.path.exists(file)

    dir2 = os.path.join(dir, 'bee')
    c.write(dir2)
    assert os.path.exists(dir2)
    assert c.path() == dir2


def test_resolve():
    assert resolve('~aaaaaaaa') == 'mem://aaaaaaaa'
    assert resolve('./report.docx') == 'file://' + os.getcwd() + '/report.docx'
    assert resolve('gh/foo/bar/report.md') == 'git://github.com/foo/bar/report.md'
    assert resolve('stats/t-test') == 'git://stenci.la/stats/t-test'


def test_obtain_mem():
    assert obtain('mem://aaaaaaaa') is None


def test_obtain_file():
    h, p = tempfile.mkstemp()
    assert obtain('file://' + p) == p


@slow
def test_obtain_http():
    assert re.match('/tmp/\w+\.html', obtain('http://docs.python.org/2/library/intro.html'))
    assert re.match('/tmp/\w+\.json', obtain('https://httpbin.org/get'))


@slow
def test_obtain_git():
    assert obtain('git://github.com/octocat/Spoon-Knife/README.md', 'bb4cc8d') == \
        os.path.join(home, 'github.com/octocat/Spoon-Knife/bb4cc8d/README.md')

    assert obtain('git://github.com/octocat/Spoon-Knife/README.md') == \
        os.path.join(home, 'github.com/octocat/Spoon-Knife/master/README.md')

    assert obtain('git://github.com/octocat/Spoon-Knife/index.html', 'master') == \
        os.path.join(home, 'github.com/octocat/Spoon-Knife/master/index.html')
