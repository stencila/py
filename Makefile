all: setup build

SETUP_PACKAGES := setuptools wheel tox twine sphinx sphinx-autobuild sphinx_rtd_theme sphinxcontrib-napoleon pylint

# A local user install is generally recommended
setup:
	pip install --user $(SETUP_PACKAGES)

# A global install is required for Travis as is the extra package `tox-travis`
setup-travis:
	pip install $(SETUP_PACKAGES) tox-travis

run:
	python -m stencila

build:
	python setup.py bdist_wheel
.PHONY: build

install:
	# Install Stencila from current source in this directory.
	pip3 install --user --upgrade .
	python3 -m stencila register

lint:
	pylint stencila

test:
ifeq ($(OS), win)
# Virtalenv fails to install on MSYS2 (see issue #200)
# So this workaround installs the latest Stencila wheel and runs tests "manually" (i.e. not using tox/virtualenv)
	pip install --user --upgrade --force-reinstall $(ls -rt dist/*.whl | tail -n 1)
	python tests/tests.py
else
	tox
endif

test-all:
	tox -e all

cover:
	tox -e cover
	sed -i "s!.tox/cover/lib/python2.7/site-packages/stencila/!!g" coverage.xml

docs:
	$(MAKE) -C docs html
.PHONY: docs

clean:
	rm -rf stencila/*.pyc build dist stencila.egg-info .tox .cache .coverage coverage.xml docs/_build
