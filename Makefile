REGISTRY=plato-docker.artifactory.swisscom.com
IMAGE=aaas/code-analyzer
PACKAGE_NAME=code_analyzer
DOCKERFILE_PATH=cicd/Dockerfile
POETRY=poetry

VERSION=dev

# See https://python-poetry.org/docs/configuration/#virtualenvsin-project
# You must remove the venv under {cache-dir}/virtualenvs if one exists, before this taking effect
export POETRY_VIRTUALENVS_IN_PROJECT=true

install:  # ci
	$(POETRY) install

clean-install:
	$(POETRY) env info --path | xargs rm -rf
	$(POETRY) env use python3.13
	$(POETRY) lock
	$(POETRY) install

test:  # ci
	$(MAKE) --keep-going install test-format test-lint test-coverage

test-lint lint:
	$(POETRY) run mypy $(PACKAGE_NAME)
	$(POETRY) run ruff check $(PACKAGE_NAME)

test-format:
	$(POETRY) run ruff format --check $(PACKAGE_NAME)

format:
	$(POETRY) run ruff format $(PACKAGE_NAME)
	$(POETRY) run ruff check --fix $(PACKAGE_NAME)

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

# If building on ARM platform (M1 Mac) use buildx plugin
# https://github.com/docker/buildx#getting-started
DOCKER_BUILD=docker build
ifeq ($(shell uname -p),arm)
	DOCKER_BUILD=docker buildx build --platform=linux/amd64 --load
endif

build:  # ci
	$(DOCKER_BUILD) \
		--build-arg "BUILD_VERSION=$(VERSION)" \
		--build-arg PLATO_ARTIFACTORY_CREDENTIALS_USR \
		--build-arg PLATO_ARTIFACTORY_CREDENTIALS_PSW \
		-t "$(REGISTRY)/$(IMAGE):$(VERSION)" \
		-f $(DOCKERFILE_PATH) \
		.

run:
	@PROJECT=$(word 2, $(MAKECMDGOALS)); \
	./run.sh "$$PROJECT"

# Allow make to ignore unknown targets (prevents issues with positional args)
%:
	@:

.PHONY: install clean-install test lint format test-lint test-coverage test-format unit-test build run
