from stencila import Sheet, components


def test():
    c = Sheet()
    assert isinstance(c, Sheet)
    assert c in components
