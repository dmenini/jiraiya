import logging
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from anthropic import AsyncAnthropicBedrock
from pydantic_ai.agent import Agent
from pydantic_ai.models import Model, ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

from doc_scribe.domain.documentation import TechnicalDoc
from doc_scribe.domain.enums import ModelName
from doc_scribe.io.code_parser import CodeBaseParser
from doc_scribe.io.markdown import read_md
from doc_scribe.settings import Settings
from doc_scribe.writer.generator import (
    generate_code_analysis,
    generate_high_level_documentation,
)

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


def create_llm_settings(settings: Settings) -> ModelSettings:
    return ModelSettings(
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        top_p=settings.top_p,
    )


def create_llm(settings: Settings, model_name: ModelName) -> Model:
    client = AsyncAnthropicBedrock(
        aws_region=settings.aws_default_region,
        aws_access_key=settings.aws_access_key_id,
        aws_secret_key=settings.aws_secret_access_key,
        aws_session_token=settings.aws_session_token,
    )
    return AnthropicModel(
        model_name=model_name.bedrock_id,
        provider=client,  # type: ignore[arg-type]
    )


def create_str_agent(llm: Model, settings: Settings, prompt: str) -> Agent[None, str]:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=prompt,
        retries=1,
    )


def create_structured_agent(llm: Model, settings: Settings, prompt: str) -> Agent[None, TechnicalDoc]:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=prompt,
        output_type=TechnicalDoc,
        retries=1,
    )


def generate_documentation(project_root: str, project_name: str | None = None) -> None:
    with Path("config.yaml").open() as fp:
        config = yaml.safe_load(fp)

    settings = Settings()
    llm = create_llm(settings, ModelName[config["agents"]["llm"]["name"]])

    root = Path(project_root)
    project_name = project_name or root.name
    parser = CodeBaseParser(codebase_path=root, blacklist=[])

    code_analyzer = create_structured_agent(llm, settings, prompt=config["tech_writer"]["system_prompt"])

    # Module-level code analysis, consisting of summary, analysis and usage info for each top module
    logger.info("Will proceed to analyse the following modules: %s", parser.source_files)
    class_data = parser.extract_ast_nodes()
    module_tree = {c.name: c.source_code for c in class_data}

    generate_code_analysis(
        code_tree=module_tree,
        agent=code_analyzer,
        filepath=Path(project_name) / "module_level_analysis",
    )

    final_doc = read_md(filepath=Path(project_name) / "module_level_analysis")

    # High level documentation of the whole codebase, using the previous code analysis as source
    writer = create_str_agent(llm, settings, prompt=config["docs_writer"]["system_prompt"])
    generate_high_level_documentation(
        documentation=final_doc,
        agent=writer,
        filepath=Path(project_name) / "high_level_documentation",
        sections=config["docs_writer"]["sections"],
    )


if __name__ == "__main__":
    # Requires path to main module in a project
    param = sys.argv[1]
    generate_documentation(param)
