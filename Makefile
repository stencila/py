all: setup build

setup:
	pip install --user setuptools wheel tox twine

build:
	python setup.py bdist_wheel
.PHONY: build

test:
ifeq ($(OS), win)
# Virtalenv fails to install on MSYS2 (see issue #200)
# So this workaround installs the latest Stencila wheel and runs tests "manually" (i.e. not using tox/virtualenv)
	pip install --user --upgrade --force-reinstall $(ls -rt dist/*.whl | tail -n 1)
	python tests/tests.py
else
	~/.local/bin/tox
endif

cover:
	~/.local/bin/tox -e cover
	sed -i "s!.tox/cover/lib/python2.7/site-packages/stencila/!!g" coverage.xml

clean:
	rm -rf build dist stencila.egg-info .tox .cache .coverage coverage.xml
