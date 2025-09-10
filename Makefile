.PHONY: all install nopyc clean test test-integration build-test-resources docs check local validate-release upload

SHELL := /usr/bin/env bash
PYTHON_BIN ?= python
PROJECT_VENV ?= venv
INTEGRATION_TEST_RERUN ?= 2
INTEGRATION_TEST_RERUN_DELAY ?= 300

all: local check test

venv:
	$(PYTHON_BIN) -m pip install virtualenv --user
	$(PYTHON_BIN) -m virtualenv $(PROJECT_VENV)

install: venv
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install .; \
	)

nopyc:
	find . -name '*.pyc' | xargs rm -f || true
	find . -name __pycache__ | xargs rm -rf || true

clean: nopyc
	rm -rf build dist *.egg-info $(PROJECT_VENV) tests/.*config

test: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev]"; \
		coverage run -m pytest -v --ignore=tests/integration -o junit_suite_name=unit && coverage report && coverage xml && coverage html; \
	)

test-integration: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev,integration]"; \
		pytest -v --ignore=tests/unit -o junit_suite_name=integration --reruns ${INTEGRATION_TEST_RERUN} --reruns-delay ${INTEGRATION_TEST_RERUN_DELAY}; \
	)

build-test-resources: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		make local; \
		python scripts/build-test-resources.py; \
	)

docs: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[docs]"; \
		sphinx-build -M html docs build/docs -n; \
	)

check: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev,docs]"; \
		mypy amazonorders; \
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

	@if [[ $$(grep "__version__ = \"${VERSION}\"" amazonorders/__init__.py) == "" ]] ; then echo "Version not bumped in amazonorders/__init__.py" & exit 1 ; fi
	@if [[ $$(grep "``==${VERSION}``" docs/index.rst) == "" ]] ; then echo "Version not bumped in docs/index.rst" & exit 1 ; fi
	@if [[ $$(grep "``==${VERSION}``" README.md) == "" ]] ; then echo "Version not bumped in README.md" & exit 1 ; fi

upload: local
	@( \
        $(PYTHON_BIN) -m pip install --upgrade twine; \
		$(PYTHON_BIN) -m build; \
		$(PYTHON_BIN) -m twine upload dist/*; \
	)
