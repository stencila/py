## `stencila/py` : Stencila for Python

[![Build status](https://travis-ci.org/stencila/py.svg?branch=master)](https://travis-ci.org/stencila/py)
[![Code coverage](https://codecov.io/gh/stencila/py/branch/master/graph/badge.svg)](https://codecov.io/gh/stencila/py)
[![Chat](https://badges.gitter.im/stencila/stencila.svg)](https://gitter.im/stencila/stencila)

### Status

![](http://blog.stenci.la/wip.png)

This is very much a work in progress. See our [main repo](https://github.com/stencila/stencila) for more details.


### Install

Right now this package isn't on PyPI, but you can install it from here:

```
pip install --user https://github.com/stencila/py/archive/master.zip
```

### Develop

Most development tasks can be run using the usual Python tool commands or `make` recipes which wrap them.

Task                                                    | `make`       |   Python tooling      
------------------------------------------------------- |--------------|--------------------------
Install dependencies                                    | `make setup` | `pip install ...`       
Run tests                                               | `make test`  | `tox`       
Run tests with coverage                                 | `make cover` | `tox -e cover`              
Build                                                   | `make build` | `./setup.py bdist_wheel`
Clean                                                   | `make clean` | `rm -rf ...`

During development a its handy to have `pytest` installed and run individual test file from the root directory like this:

```
python -m pytest tests/test_component.py
```

Or run all the tests:

```
python -m pytest tests
```

For the automation and standardisation of testing across Python versions we use [`tox`](https://tox.readthedocs.io/en/latest/). Running `make test` (or just `tox`) will build the package and run the test suite under Python 2.7 and 3.5. 

For test coverage, the test suite is run under Python 2.7 only. Coverage is run on the build at https://travis-ci.org/stencila/py and displayed at https://codecov.io/gh/stencila/py.
