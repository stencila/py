## Stencila for Python

[![Build status](https://travis-ci.org/stencila/py.svg?branch=master)](https://travis-ci.org/stencila/py)
[![Code coverage](https://codecov.io/gh/stencila/py/branch/master/graph/badge.svg)](https://codecov.io/gh/stencila/py)
[![Documentation](https://readthedocs.org/projects/stencila-for-python/badge/)](http://stencila-for-python.readthedocs.io)
[![Chat](https://badges.gitter.im/stencila/stencila.svg)](https://gitter.im/stencila/stencila)

### Install

This package isn't on PyPI yet, but you can install it this repository using using pip:

```
pip install --user https://github.com/stencila/py/archive/master.zip
```

### Use

This package lets you run Python code from inside Stencila Documents. First, you need to start serving the Stencila Host within this package. You can do that in your favourite Python console:

```python
import stencila
stencila.start()
```

Or at the system shell:

```sh
python -m stencila
```

Then, open your Stencila Document from within the [Stencila Desktop](https://github.com/stencila/desktop). The host will be automatically detected by the dektop app and you'll be able to execute Python & SQLite code cells from within your documents.

More documentation is available at http://stencila-for-python.readthedocs.io

### Discuss

We love feedback. Create a [new issue](https://github.com/stencila/py/issues/new), add to [existing issues](https://github.com/stencila/py/issues) or [chat](https://gitter.im/stencila/stencila) with members of the community.

### Develop

Most development tasks can be run using the usual Python toolchain or via `make` shortcuts.

Task                                                    | `make`       |   Python tooling      
------------------------------------------------------- |--------------|--------------------------
Install dependencies                                    | `make setup` | `pip install ...`       
Run tests                                               | `make test`  | `tox`       
Run tests with coverage                                 | `make cover` | `tox -e cover`              
Build                                                   | `make build` | `./setup.py bdist_wheel`
Clean                                                   | `make clean` | `rm -rf ...`

To get started, please read our contributor [code of conduct](CONDUCT.md), then [get in touch](https://gitter.im/stencila/stencila) or checkout the [platform-wide, cross-repository kanban board](https://github.com/orgs/stencila/projects/1), or just send in a pull request!

During development a its handy to have `pytest` installed and run individual test file from the root directory like this:

```
python -m pytest tests/test_component.py
```

Or run all the tests:

```
python -m pytest tests
```

For the automation and standardisation of testing across Python versions we use [`tox`](https://tox.readthedocs.io/en/latest/). Running `make test` (or just `tox`) will build the package and run the test suite.

Tests are run on [Travis](https://travis-ci.org/stencila/py) and code coverage tracked at [Codecov](https://codecov.io/gh/stencila/py).
