from pathlib import Path

import pytest
from pydantic_ai.agent import Agent
from pydantic_ai.models.test import TestModel
from pytest_mock import MockerFixture

from doc_scribe.domain.documentation import TechnicalDoc
from doc_scribe.writer.generator import (
    _remove_before_start_and_after_end,
    generate_code_analysis,
    generate_docs_for_file,
    generate_high_level_documentation,
    write_code_analysis,
)


@pytest.fixture
def structured_agent() -> Agent[None, TechnicalDoc]:
    llm = TestModel()
    return Agent(model=llm, result_type=TechnicalDoc)


@pytest.fixture
def str_agent() -> Agent[None, str]:
    llm = TestModel()
    return Agent(model=llm)


def test_generate_docs_for_file(structured_agent: Agent[None, TechnicalDoc]) -> None:
    code = "mock code"
    result = generate_docs_for_file(code=code, writer=structured_agent)

    assert result == TechnicalDoc(summary="a", analysis="a", usage="a")


def test_generate_code_analysis(structured_agent: Agent[None, TechnicalDoc], mocker: MockerFixture) -> None:
    mock_file = Path("mock_filepath.json")
    mock_code_tree = {"file1.py": "code1", "file2.py": "code2"}

    mocker.patch("doc_scribe.writer.generator.read_json", side_effect=FileNotFoundError)
    mocker.patch("doc_scribe.writer.generator.write_json_as_md")

    result = generate_code_analysis(code_tree=mock_code_tree, agent=structured_agent, filepath=mock_file)

    assert set(result.keys()) == {"file1.py", "file2.py"}


def test_write_code_analysis(mocker: MockerFixture) -> None:
    doc = TechnicalDoc(summary="a", analysis="a", usage="a")
    mock_file_docs = {"file1.py": doc, "file2.py": doc}
    mock_module_docs = {"module": doc}
    mock_path = Path("mock_project/docs.md")

    for doc in mock_file_docs.values():
        doc.to_markdown.return_value = "# File Doc\n"
    for doc in mock_module_docs.values():
        doc.to_markdown.return_value = "# Module Doc\n"

    mocker.patch("doc_scribe.writer.generator.write_md")

    result = write_code_analysis(file_docs=mock_file_docs, module_docs=mock_module_docs, filepath=mock_path)

    assert "# File Doc" in result
    assert "# Module Doc" in result


def test_remove_before_start_and_after_end() -> None:
    input_text = "Some text [START] Important content [END] Extra text"
    expected_output = " Important content "

    assert _remove_before_start_and_after_end(input_text) == expected_output


def test_generate_high_level_documentation(str_agent: Agent[None, str], mocker: MockerFixture) -> None:
    mock_filepath = Path("mock_project/docs.md")

    mocker.patch("doc_scribe.writer.generator.write_md")

    result = generate_high_level_documentation(
        agent=str_agent, documentation="mock documentation", filepath=mock_filepath
    )

    assert result == (
        "# Mock Project Documentation\n\n"
        "## 1. Summary\n\n"
        "success (no tool calls)\n\n"
        "## 2. Architecture Overview\n\n"
        "success (no tool calls)\n\n"
        "## 3. Data Flow\n\n"
        "success (no tool calls)\n\n"
        "## 4. Security Concerns\n\n"
        "success (no tool calls)\n\n"
        "## 5. Key Modules & Responsibilities\n\n"
        "success (no tool calls)\n\n"
        "## 6. Cross Cutting Concerns\n\n"
        "success (no tool calls)\n\n"
    )
