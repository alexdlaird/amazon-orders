.PHONY: all virtualenv install nopyc clean test test-integration test-integration-generic test-integration-json build-test-resources docs check local validate-release upload

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
		python -m pip install .; \
	)

nopyc:
	find . -name '*.pyc' | xargs rm -f || true
	find . -name __pycache__ | xargs rm -rf || true

clean: nopyc
	rm -rf build dist *.egg-info venv

test: virtualenv
	@( \
		source venv/bin/activate; \
		python -m pip install ".[dev]"; \
		coverage run -m pytest -v --ignore=tests/integration && coverage report && coverage xml && coverage html; \
	)

test-integration: virtualenv
	@( \
		source venv/bin/activate; \
		python -m pip install ".[dev]"; \
		python amazonorders/cli.py --username $(AMAZON_USERNAME) --password $(AMAZON_PASSWORD) login; \
		coverage run -m pytest -v --rootdir=tests/integration; \
	)

build-test-resources: virtualenv
	@( \
		source venv/bin/activate; \
		make local; \
		python scripts/build-test-resources.py; \
	)

docs: virtualenv
	@( \
		source venv/bin/activate; \
		python -m pip install ".[docs]"; \
		sphinx-build -M html docs build/docs -n; \
	)

check: virtualenv
	@( \
		source venv/bin/activate; \
		python -m pip install ".[dev,docs]"; \
		mypy amazonorders || true; \
		flake8; \
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

	@if [[ $$(grep "__version__ = \"${VERSION}\"" amazonorders/__init__.py) == "" ]] ; then echo "Version not bumped in amazonrders/__init__.py" & exit 1 ; fi

upload: local
	@( \
        $(PYTHON_BIN) -m pip install --upgrade twine; \
		$(PYTHON_BIN) -m build; \
		$(PYTHON_BIN) -m twine upload dist/*; \
	)
