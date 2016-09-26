from os.path import dirname, abspath

from stencila.document import Document, DocumentXmd

here = dirname(abspath(__file__)) + '/'


def test_load_pre():
    c = DocumentXmd()
    assert c.load_pre('```{r}\n', 'r') == '``` {.r}\n'
    assert c.load_pre('``` {r}\n', 'r') == '``` {.r}\n'

    assert c.load_pre('```{r label}\n', 'r') == '``` {.r #label}\n'
    assert c.load_pre('```{r label, fig.height=7}\n', 'r') == '``` {.r #label fig.height="7"}\n'
    assert c.load_pre('```{r label, fig.height=7, fig.width=6}\n', 'r') == '``` {.r #label fig.height="7" fig.width="6"}\n'


def test_load_post():
    c = DocumentXmd()
    d = Document()

    d.html = '<pre id="chunk-1" class="py"><code>x = 42</code></pre>'
    c.load_post(d, 'py')
    assert d.dump(pretty=False) == '''<pre id="chunk-1" data-execute="py">x = 42</pre>'''

    d.html = '<pre class="r" fig.width="6" fig.height="7"><code>plot(x)</code></pre>'
    c.load_post(d, 'r')
    assert d.dump(pretty=False) == '''<pre data-execute="r width 6 height 7">plot(x)</pre>'''

    d.html = '<code>js x</code>'
    c.load_post(d, 'js')
    assert d.dump(pretty=False) == '''<span data-print="js x"></span>'''


def test_load():
    c = DocumentXmd()
    d = Document()

    c.load(d, '''
``` {r}
x <- 42
```

The answer `r x`

``` {r my-plot fig.width=6, fig.height=7}
plot(x)
```
''', 'rmd')

    assert d.html == '''
<pre data-execute="r">x &lt;- 42</pre>
<p>The answer <span data-print="r x"></span></p>

<pre id="my-plot" data-execute="r width 6 height 7">plot(x)</pre>
'''.strip()
