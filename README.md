# Code Analyzer

## Local Development

### Prerequisites

1. Export the Artifactory credentials as env variables:
   ```bash
   export POETRY_HTTP_BASIC_ARTIFACTORY_USERNAME=$PLATO_ARTIFACTORY_CREDENTIALS_USR
   export POETRY_HTTP_BASIC_ARTIFACTORY_PASSWORD=$PLATO_ARTIFACTORY_CREDENTIALS_PSW
   ```
2. Run `make install` to install the developments requirements (including runtime requirements).

### Run Service Locally

1. Make sure the local stack is running.
2. Export the AWS variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN`
3. Run the service: `make run`.

### Tests

To run tests with pytest, use one of the following commands:

```bash
# Run tests with coverage + linting (as CI)
make test 

# Run all unit tests with coverage
make test-coverage

# Run all unit tests (without coverage)
make unit-test

# Run a specific test case or file
make unit-test TEST_FILE=path/to/test::test_case
```

### Lint and Format

We use these dev tools for linting and formatting:

- [ruff](https://docs.astral.sh/ruff/) as linter and formatter
- [mypy](https://mypy.readthedocs.io/en/stable/) as static type checker

To use them, run one of the following commands:

```bash
# Check linting, type hints
make lint

# Check format errors
make test-format

# Fix format with ruff and sort imports
make format
```
