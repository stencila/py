## Stencila for Python

[![Build status](https://travis-ci.org/stencila/py.svg?branch=master)](https://travis-ci.org/stencila/py)
[![Code coverage](https://codecov.io/gh/stencila/py/branch/master/graph/badge.svg)](https://codecov.io/gh/stencila/py)
[![Documentation](https://readthedocs.org/projects/stencila-for-python/badge/)](http://stencila-for-python.readthedocs.io)
[![Community](https://img.shields.io/badge/join-community-green.svg)](https://community.stenci.la)
[![Chat](https://badges.gitter.im/stencila/stencila.svg)](https://gitter.im/stencila/stencila)

### Install

This package isn't on PyPI yet, but you can install it this repository using using `pip`:

```bash
pip install --user https://github.com/stencila/py/archive/master.zip
```

**Note** If you have [Anaconda](https://www.anaconda.com/) installed on your system, you should install the package using the following command:

```bash
pip install https://github.com/stencila/py/archive/master.zip
```

This will install `stencila` in your Anaconda directory (where it should be), rather than in your local user Python libraries directory.
If you don't do that (i.e. get the `stencila` package installed in your local user Python libraries), when you try to register `stencila`
package (see below), you will get an error as your Anaconda Python will search for `stencila` and its dependencies in the Anaconda directory.   


Then install the package so that other Stencila packages and applications can detect it:


```bash
python -m stencila register
```

or, for older versions of Python you may need to do:

```bash
python -c "import stencila; stencila.register()"
```

### Use

This package lets you run Python code (and other languages) from inside Stencila Documents. When you start the [Stencila Desktop](https://github.com/stencila/desktop), the Stencila Python package will be automatically detected by the dektop app and you'll be able to execute Python code cells from within your documents.

In addition to the a `PythonContext` class, this packages also provides a `SQLiteContext` for executing SQL within an SQLite database (currently only an in-memory database).

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
Build documentation                                     | `make docs`  | `make -C docs html`
Run for manual testing                                  | `make run`   | `python -m stencila`
Clean                                                   | `make clean` | `rm -rf ...`

To get started, please read our contributor [code of conduct](CONDUCT.md), then [get in touch](https://gitter.im/stencila/stencila) or checkout the [platform-wide, cross-repository kanban board](https://github.com/orgs/stencila/projects/1), or just send in a pull request!

During development a its handy to have `pytest` installed and run individual test file from the root directory like this:

```
python -m pytest tests/test_python_context.py
```

Or run all the tests:

```
python -m pytest tests
```

For the automation and standardisation of testing across Python versions we use [`tox`](https://tox.readthedocs.io/en/latest/). Running `make test` (or just `tox`) will build the package and run the test suite.

Tests are run on [Travis](https://travis-ci.org/stencila/py) and code coverage tracked at [Codecov](https://codecov.io/gh/stencila/py).
