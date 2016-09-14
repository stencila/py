import tempfile
import os

import pytest

from stencila import Component, components


def test_new():
    c = Component()
    assert isinstance(c, Component)
    assert c in components


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
    c = Component('foo/bar')  # This is OK

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
