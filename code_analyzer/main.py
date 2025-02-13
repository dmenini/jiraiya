import logging
import sys
from pathlib import Path

from anthropic import AsyncAnthropicBedrock
from pydantic_ai.agent import Agent
from pydantic_ai.models import Model, ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

from code_analyzer.domain.documentation import TechnicalDoc
from code_analyzer.domain.enums import ModelName
from code_analyzer.io.code_loader import CodebaseLoader
from code_analyzer.prompts.system_prompt import (
    CODE_ANALYSIS_PROMPT,
    WRITER_SYSTEM_PROMPT,
)
from code_analyzer.settings import Settings
from code_analyzer.writer.generator import (
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

    # File level docs, to be used as chunks and in plato docs (low level section)
    tree = loader.load_all_files()
    file_docs = generate_code_analysis(
        code_tree=tree,
        agent=code_analyzer,
        filepath=Path(root.name) / "file_level_analysis",
    )

    # Top module level docs
    module_tree = loader.load_all_modules()
    module_docs = generate_code_analysis(
        code_tree=module_tree,
        agent=code_analyzer,
        filepath=Path(root.name) / "module_level_analysis",
    )

    # Overall tech docs, to be used in plato docs (mid level section)
    final_doc = write_code_analysis(
        file_docs=file_docs,
        module_docs=module_docs,
        filepath=Path(root.name) / "code_analysis",
    )

    # Overall docs, to be used in plato docs (high level section)
    writer = create_str_agent(llm, settings, prompt=WRITER_SYSTEM_PROMPT)
    generate_high_level_documentation(
        documentation=final_doc,
        agent=writer,
        filepath=Path(root.name) / "high_level_documentation",
    )


if __name__ == "__main__":
    # Requires path to main module in a project (e.g. chat-api/chat_api)
    param = sys.argv[1]
    generate_documentation(param)
