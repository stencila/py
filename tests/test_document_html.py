from os.path import dirname, abspath

from stencila.document import Document, DocumentHtml


def test_simple():
    d = Document()
    c = DocumentHtml()

    html = '<p>Para1</p><ol><li>One</li><li>Two</li></ol>'
    c.load(d, html)

    assert c.dump(d, pretty=False) == html
    assert c.dump(d, pretty=True) == '''
<p>Para1</p>
<ol>
  <li>One</li>
  <li>Two</li>
</ol>
'''.strip()
