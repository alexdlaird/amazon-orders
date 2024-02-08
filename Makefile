.PHONY: all virtualenv install nopyc clean test test-integration test-integration-generic test-integration-json build-test-resources docs local validate-release upload

SHELL := /usr/bin/env bash
PYTHON_BIN ?= python

all: virtualenv install

virtualenv:
	@if [ ! -d "venv" ]; then \
		$(PYTHON_BIN) -m pip install virtualenv --user; \
		$(PYTHON_BIN) -m virtualenv venv; \
	fi

install: virtualenv
	@( \
		source venv/bin/activate; \
		python -m pip install -r requirements.txt -r requirements-dev.txt; \
	)

nopyc:
	find . -name '*.pyc' | xargs rm -f || true
	find . -name __pycache__ | xargs rm -rf || true

clean: nopyc
	rm -rf _build dist *.egg-info venv

test: install
	@( \
		source venv/bin/activate; \
		python -m coverage run -m unittest discover -v -b && python -m coverage xml && python -m coverage html && python -m coverage report; \
	)

test-integration: install
	@( \
		source venv/bin/activate; \
		INTEGRATION_TEST=True python -m unittest discover -v -b; \
	)

test-integration-generic: install
	@( \
		source venv/bin/activate; \
		INTEGRATION_TEST_GENERIC=True python -m unittest discover -v -b; \
	)

test-integration-json: install
	@( \
		source venv/bin/activate; \
		INTEGRATION_TEST_JSON=True python -m unittest discover -v -b; \
	)

build-test-resources: install
	@( \
		source venv/bin/activate; \
		make local; \
		python scripts/build-test-resources.py; \
	)

docs: install
	@( \
		source venv/bin/activate; \
		python -m pip install -r docs/requirements.txt; \
		mypy amazonorders; \
		sphinx-build -M html docs _build/docs -n; \
	)

local:
	@rm -rf *.egg-info dist
	@( \
		$(PYTHON_BIN) -m pip install --upgrade pip; \
        $(PYTHON_BIN) -m pip install --upgrade build; \
		$(PYTHON_BIN) -m build; \
		$(PYTHON_BIN) -m pip install dist/*.tar.gz; \
	)

validate-release:
	@if [[ "${VERSION}" == "" ]]; then echo "VERSION is not set" & exit 1 ; fi

	@if [[ $$(grep "version = \"${VERSION}\"" pyproject.toml) == "" ]] ; then echo "Version not bumped in pyproject.toml" & exit 1 ; fi
	@if [[ $$(grep "__version__ = \"${VERSION}\"" amazonorders/cli.py) == "" ]] ; then echo "Version not bumped in amazonrders/cli.py" & exit 1 ; fi

upload: local
	@( \
        $(PYTHON_BIN) -m pip install --upgrade twine; \
		$(PYTHON_BIN) -m build; \
		$(PYTHON_BIN) -m twine upload dist/*; \
	)
