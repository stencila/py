from stencila import session, Context


def test_new():
    c = Context()
    assert isinstance(c, Context)
    assert c in session.components
