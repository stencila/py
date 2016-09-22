from stencila import session, Sheet


def test():
    s = Sheet()
    assert s in session.components
    assert isinstance(s, Sheet)
