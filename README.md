# Doc Scribe

`doc-scribe` is an intelligent documentation tool that transforms code analysis into structured, developer-friendly
documentation. Powered by LLMs, it automatically extracts insights from your codebase, generating high-quality
documentation at multiple levels:

* Module-Level Analysis – Understand the architecture and high-level design.
* File-Level Insights – Capture granular details for deeper understanding.
* Comprehensive Tech Docs – Generate well-structured documentation for your team.

* Whether you're working with small projects or large-scale applications, `doc-scribe` ensures that your documentation
  remains up-to-date, accurate, and useful—without the manual effort.

**Turn your code into clear, maintainable documentation with doc-scribe.**

## Local Development

### Prerequisites

Run `make install` to install the developments requirements (including runtime requirements).

### Run Service Locally

1. Export the AWS variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN`
2. Run the service: `make run <project_name>`.

> The make run target will look for the project with the given name recursively from the Desktop folder.

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
