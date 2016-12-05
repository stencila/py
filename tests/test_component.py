import tempfile
import os
import re

import pytest

from stencila import host, Component


def test_new():
    c = Component()
    assert isinstance(c, Component)
    assert c in host.components
    assert host.open(c.address) is c
    assert re.match('^id://[a-z0-9]+$', c.address)
    assert repr(c) == 'Component(%s)' % c.address


def test_del():
    l1 = len(host.components)
    c = Component()
    l2 = len(host.components)
    c.__del__()
    l3 = len(host.components)

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
