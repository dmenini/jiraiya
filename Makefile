PACKAGE_NAME=doc_scribe
UV=uv

VERSION=dev

install:  # ci
	$(UV) sync

clean-install:
	rm -rf .venv
	$(UV) lock
	$(UV) sync

test:  # ci
	$(MAKE) --keep-going install test-format test-lint test-coverage

test-lint lint:
	$(UV) run mypy $(PACKAGE_NAME) tests
	$(UV) run ruff check $(PACKAGE_NAME) tests

test-format:
	$(UV) run ruff format --check $(PACKAGE_NAME) tests

format:
	$(UV) run ruff format $(PACKAGE_NAME) tests
	$(UV) run ruff check --fix $(PACKAGE_NAME) tests

test-coverage:
	$(UV) run pytest \
		--capture=no \
		--cov \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=xml \
		--junit-xml=report.xml \
		tests

TEST_TARGET ?= tests/

unit-test:
	$(UV) run pytest $(TEST_TARGET)

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
	$(UV) run ./run.sh

.PHONY: install clean-install test lint format test-lint test-coverage test-format unit-test build run
