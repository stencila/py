from stencila import Context, components


def test_new():
    c = Context()
    assert isinstance(c, Context)
    assert c in components
