from stencila import Session, components

def test():
    c = Session()
    assert isinstance(c, Session)
    assert c in components
