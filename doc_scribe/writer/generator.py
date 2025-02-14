import logging
from pathlib import Path

from pydantic_ai.agent import Agent

from doc_scribe.domain.documentation import TechnicalDoc
from doc_scribe.io.markdown import read_json, write_json_as_md, write_md
from doc_scribe.prompts.system_prompt import (
    ARCHITECTURE_PROMPT,
    CONCERNS_PROMPT,
    DATA_FLOW_PROMPT,
    MODULES_PROMPT,
    SECURITY_PROMPT,
    SUMMARY_PROMPT,
)

logger = logging.getLogger(__name__)


def generate_docs_for_file(code: str, writer: Agent[None, TechnicalDoc]) -> TechnicalDoc:
    response = writer.run_sync(user_prompt=code)
    documentation = response.data
    return documentation


def generate_code_analysis(
    code_tree: dict[str, str],
    agent: Agent[None, TechnicalDoc],
    filepath: Path,
) -> dict[str, TechnicalDoc]:
    try:
        file_docs = read_json(filepath)
        logger.info("Loaded %d docs from %s", len(file_docs), filepath)
    except FileNotFoundError:
        file_docs = {}
        for path, code in code_tree.items():
            logger.info("Processing %s", path)
            file_docs[path] = generate_docs_for_file(code=code, writer=agent)

        write_json_as_md(file_docs, filepath=filepath)

    return file_docs


def write_code_analysis(
    file_docs: dict[str, TechnicalDoc], module_docs: dict[str, TechnicalDoc], filepath: Path
) -> str:
    project_name = filepath.parts[0]
    name = project_name.replace("_", " ").title()
    final_doc = f"# {name} Technical Documentation\n\n"

    modules = sorted(module_docs.keys())
    top_level_files = sorted(path for path in file_docs if not any(path.startswith(module) for module in modules))

    for file in top_level_files:
        final_doc += file_docs[file].to_markdown(path=file, template="standalone")

    for module in modules:
        final_doc += module_docs[module].to_markdown(path=module, template="header")

        files = sorted([file for file in file_docs if file.startswith(module)])
        for file in files:
            final_doc += file_docs[file].to_markdown(path=file, template="subsection")

    write_md(final_doc, filepath=filepath)

    return final_doc


def _remove_before_start_and_after_end(text: str) -> str:
    marker = "[START]"
    index = text.find(marker)
    if index != -1:
        text = text[index + len(marker) :]

    marker = "[END]"
    index = text.find(marker)
    if index != -1:
        text = text[:index]

    return text


def generate_high_level_documentation(agent: Agent[None, str], documentation: str, filepath: Path) -> str:
    project_name = filepath.parts[0]

    sections = {
        "1. Summary": SUMMARY_PROMPT,
        "2. Architecture Overview": ARCHITECTURE_PROMPT,
        "3. Data Flow": DATA_FLOW_PROMPT,
        "4. Security Concerns": SECURITY_PROMPT,
        "5. Key Modules & Responsibilities": MODULES_PROMPT,
        "6. Cross Cutting Concerns": CONCERNS_PROMPT,
    }

    name = project_name.replace("_", " ").title()
    hl_documentation = f"# {name} Documentation\n\n"
    for section, template in sections.items():
        user_prompt = template.format(documentation=documentation)
        response = agent.run_sync(user_prompt=user_prompt)
        result = response.data

        # Postprocess the result
        section_doc = _remove_before_start_and_after_end(result)
        section_doc = section_doc.strip("\n")

        hl_documentation += f"## {section}\n\n{section_doc}\n\n"

    write_md(hl_documentation, filepath=filepath)

    return hl_documentation
