PACKAGE_NAME=doc_scribe
POETRY=poetry

VERSION=dev

# See https://python-poetry.org/docs/configuration/#virtualenvsin-project
# You must remove the venv under {cache-dir}/virtualenvs if one exists, before this taking effect
export POETRY_VIRTUALENVS_IN_PROJECT=true

install:
	$(POETRY) install

clean-install:
	$(POETRY) env info --path | xargs rm -rf
	$(POETRY) env use python3.13
	$(POETRY) lock
	$(POETRY) install

test:
	$(MAKE) --keep-going install test-format test-lint test-coverage

lint:
	$(POETRY) run mypy $(PACKAGE_NAME) tests
	$(POETRY) run ruff check $(PACKAGE_NAME) tests
	$(POETRY) run ruff format --check $(PACKAGE_NAME) tests

format:
	$(POETRY) run ruff format $(PACKAGE_NAME) tests
	$(POETRY) run ruff check --fix $(PACKAGE_NAME) tests

test-coverage:
	$(POETRY) run pytest \
		--capture=no \
		--cov \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=xml \
		--junit-xml=report.xml \
		tests

TEST_TARGET ?= tests/

unit-test:
	$(POETRY) run pytest $(TEST_TARGET)

run:
	@PROJECT=$(word 2, $(MAKECMDGOALS)); \
	./run.sh "$$PROJECT"

# Allow make to ignore unknown targets (prevents issues with positional args)
%:
	@:

.PHONY: install clean-install test lint format test-coverage unit-test build run
