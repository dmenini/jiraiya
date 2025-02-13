import logging
from pathlib import Path

from pydantic_ai.agent import Agent

from code_analyzer.domain.documentation import TechnicalDoc
from code_analyzer.io.markdown import read_json, write_json_as_md

CODE_SEPARATOR = "\n\n==================================\n\n"

logger = logging.getLogger()


def generate_docs_for_file(code: str, writer: Agent[None, TechnicalDoc]) -> TechnicalDoc:
    response = writer.run_sync(user_prompt=code)
    documentation = response.data
    return documentation


def generate_code_analysis(
    code_tree: dict[str, str],
    agent: Agent[None, TechnicalDoc],
    filepath: Path,
    *,
    load_from_file: bool,
) -> dict[str, TechnicalDoc]:
    if load_from_file:
        file_docs = read_json(filepath)
    else:
        file_docs = {}
        for path, code in code_tree.items():
            logger.info("Processing %s", path)
            file_docs[path] = generate_docs_for_file(code=code, writer=agent)

        write_json_as_md(file_docs, file_name=filepath)

    return file_docs
