import logging
import sys
from pathlib import Path

from anthropic import AsyncAnthropicBedrock
from pydantic_ai.agent import Agent
from pydantic_ai.models import Model, ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

from doc_scribe.domain.documentation import TechnicalDoc
from doc_scribe.domain.enums import ModelName
from doc_scribe.io.code_loader import CodebaseLoader
from doc_scribe.io.markdown import read_md
from doc_scribe.prompts.system_prompt import (
    CODE_ANALYSIS_PROMPT,
    WRITER_SYSTEM_PROMPT,
)
from doc_scribe.settings import Settings
from doc_scribe.writer.generator import (
    generate_code_analysis,
    generate_high_level_documentation,
    write_code_analysis,
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
        anthropic_client=client,  # type: ignore[arg-type]
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
        result_type=TechnicalDoc,
        retries=1,
    )


def generate_documentation(project_root: str) -> None:
    settings = Settings()
    llm = create_llm(settings, ModelName.CLAUDE_3_5_SONNET)

    root = Path(project_root)
    loader = CodebaseLoader(root_path=root)

    code_analyzer = create_structured_agent(llm, settings, prompt=CODE_ANALYSIS_PROMPT)

    # Module-level code analysis, consisting of summary, analysis and usage info for each top module
    module_tree = loader.load_all_modules()
    module_docs = generate_code_analysis(
        code_tree=module_tree,
        agent=code_analyzer,
        filepath=Path(root.name) / "module_level_analysis",
    )

    tree = loader.load_all_files()
    if len(tree) < settings.max_file_count:
        # File-level code analysis, consisting of summary, analysis and usage info for each file
        file_docs = generate_code_analysis(
            code_tree=tree,
            agent=code_analyzer,
            filepath=Path(root.name) / "file_level_analysis",
        )

        # Integrate module and file docs into a comprehensive documentation, trying to avoid redundancy
        final_doc = write_code_analysis(
            file_docs=file_docs,
            module_docs=module_docs,
            filepath=Path(root.name) / "code_analysis",
        )

    else:
        # In case of too many files we simply use the module analysis
        logger.info("Found %d files in the project: file level analysis skipped", len(tree))
        final_doc = read_md(filepath=Path(root.name) / "module_level_analysis")

    # High level documentation of the whole codebase, using the previous code analysis as source
    writer = create_str_agent(llm, settings, prompt=WRITER_SYSTEM_PROMPT)
    generate_high_level_documentation(
        documentation=final_doc,
        agent=writer,
        filepath=Path(root.name) / "high_level_documentation",
    )


if __name__ == "__main__":
    # Requires path to main module in a project
    param = sys.argv[1]
    generate_documentation(param)
