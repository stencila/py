from os.path import dirname, abspath

from stencila import instance, Sheet

here = dirname(abspath(__file__)) + '/'


def test_new():
    s = Sheet()
    assert isinstance(s, Sheet)
    assert s.type == 'sheet'
    assert s in instance.components
    assert instance.open(s.address) is s

