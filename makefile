SHELL = /usr/bin/env bash

APPLEUTILOGLEVEL ?= DEBUG
python ?= python
_python = APPLEUTILOGLEVEL=$(APPLEUTILOGLEVEL) $(python)
pandoc ?= pandoc
_pandoc = APPLEUTILOGLEVEL=$(APPLEUTILOGLEVEL) $(pandoc)
# use pytest-parallel if python < 3.9 else pytest-xdist
# as pytest-parallel is faster but doesn't support python 3.9 yet
PYTESTARGS ?= $(shell python -c 'import sys; print("--workers auto" if sys.version_info < (3, 9) else "-n auto")')
COVHTML ?= --cov-report html
# for bump2version, valid options are: major, minor, patch
PART ?= patch

pandocArgs = --toc -M date="`date "+%B %e, %Y"`" --filter=pantable --wrap=none

RSTs = CHANGELOG.rst README.rst

# Main Targets #################################################################

.PHONY: test docs-all docs html epub clean Clean

all: editable
	$(MAKE) test docs-all

test:
	$(_python) -m pytest -vv $(PYTESTARGS) \
		--cov=src --cov-report term $(COVHTML) --no-cov-on-fail --cov-branch \
		tests

clean:
	rm -f .coverage* docs/apple_uti*.rst docs/modules.rst docs/setup.rst setup.py
	rm -rf htmlcov apple_uti.egg-info .cache .idea dist docs/_build \
		docs/_static docs/_templates .ipynb_checkpoints .mypy_cache \
		.pytest_cache .tox
	find . -type f -name "*.py[co]" -delete \
		-or -type d -name "__pycache__" -delete
Clean: clean
	rm -f $(RSTs)

# maintenance ##################################################################

.PHONY: pypi pypiManual pep8 flake8 pylint
# Deploy to PyPI
## by CI, properly git tagged
pypi:
	git push origin v0.1.0
## Manually
pypiManual:
	rm -rf dist
	tox -e check
	poetry build
	twine upload dist/*

# check python styles
pep8:
	pycodestyle . --ignore=E501
flake8:
	flake8 . --ignore=E501
pylint:
	pylint apple_uti

print-%:
	$(info $* = $($*))

# docs #########################################################################

README.rst: docs/README.md docs/badges.csv
	printf \
		"%s\n\n" \
		".. This is auto-generated from \`$<\`. Do not edit this file directly." \
		> $@
	cd $(<D); \
	$(_pandoc) $(pandocArgs) $(<F) -V title='apple_uti Documentation' -s -t rst \
		>> ../$@

%.rst: %.md
	printf \
		"%s\n\n" \
		".. This is auto-generated from \`$<\`. Do not edit this file directly." \
		> $@
	$(_pandoc) $(pandocArgs) $< -s -t rst >> $@

dist/docs/:
	tox -e docs

# poetry #######################################################################

setup.py:
	poetry build
	cd dist; tar -xf apple_uti-0.1.0.tar.gz apple_uti-0.1.0/setup.py
	mv dist/apple_uti-0.1.0/setup.py .
	rm -rf dist/apple_uti-0.1.0

# since poetry doesn't support editable, we can build and extract the setup.py,
# temporary remove pyproject.toml and ask pip to install from setup.py instead.
editable: setup.py
	mv pyproject.toml .pyproject.toml
	$(_python) -m pip install --no-dependencies -e .
	mv .pyproject.toml pyproject.toml

# releasing ####################################################################

bump:
	bump2version $(PART)
	git push --follow-tags
