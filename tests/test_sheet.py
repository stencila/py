from stencila import instance, Sheet


def test():
    s = Sheet()
    assert s in instance.components
    assert isinstance(s, Sheet)
