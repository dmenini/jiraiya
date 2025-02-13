from pathlib import Path

from anthropic import AsyncAnthropicBedrock
from pydantic_ai.agent import Agent
from pydantic_ai.models import Model, ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

from code_analyzer.domain.documentation import TechnicalDoc
from code_analyzer.domain.enums import ModelName
from code_analyzer.io.code_loader import CodebaseLoader
from code_analyzer.io.markdown import read_json, write_json_as_md, write_md
from code_analyzer.prompts.system_prompt import (
    CODE_ANALYSIS_PROMPT,
    TECH_WRITER_SYSTEM_PROMPT,
    WRITER_SYSTEM_PROMPT,
)
from code_analyzer.settings import Settings
from code_analyzer.writer.generator import generate_docs_for_file

LOAD_FROM_FILE = True


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


def generate_code_analysis(
    code_tree: dict[str, str],
    agent: Agent[None, TechnicalDoc],
    filepath: Path,
) -> dict[str, TechnicalDoc]:
    if LOAD_FROM_FILE:
        file_docs = read_json(filepath)
    else:
        file_docs = {}
        for path, code in code_tree.items():
            print(f"Processing {path}")
            file_docs[path] = generate_docs_for_file(code=code, writer=agent)

        write_json_as_md(file_docs, file_name=filepath)

    return file_docs


def write_code_analysis(project_name: str, file_docs: dict[str, TechnicalDoc],
                        module_docs: dict[str, TechnicalDoc]) -> str:
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

    write_md(final_doc, file_name=Path(project_name) / "code_analysis")

    return final_doc


def generate_documentation():
    settings = Settings()
    llm = create_llm(settings, ModelName.CLAUDE_3_5_SONNET)

    root = Path("/Users/taamedag/Desktop/cai/aaas/chat-api/chat_api")
    loader = CodebaseLoader(root_path=root, exclude=[], include=[])

    code_analyzer = create_structured_agent(llm, settings, prompt=CODE_ANALYSIS_PROMPT)

    # File level docs, to be used as chunks and in plato docs (low level section)
    tree = loader.load_all_files()
    file_docs = generate_code_analysis(
        code_tree=tree, agent=code_analyzer, filepath=Path(root.name) / "file_level_analysis",
    )

    # Top module level docs
    module_tree = loader.load_all_modules()
    module_docs = generate_code_analysis(
        code_tree=module_tree, agent=code_analyzer, filepath=Path(root.name) / "module_level_analysis",
    )

    # Overall tech docs, to be used in plato docs (mid level section)
    final_doc = write_code_analysis(project_name=root.name, file_docs=file_docs, module_docs=module_docs)

    # Overall docs, to be used in plato docs (high level tech section)
    tech_writer = create_str_agent(llm, settings, prompt=TECH_WRITER_SYSTEM_PROMPT)
    response = tech_writer.run_sync(user_prompt=final_doc)
    final_documentation = response.data
    write_md(final_documentation, file_name=Path(root.name) / "overall_analysis")

    # Overall docs, to be used in plato docs (high level section)
    writer = create_str_agent(llm, settings, prompt=WRITER_SYSTEM_PROMPT)
    response = writer.run_sync(user_prompt=final_doc)
    final_documentation = response.data
    write_md(final_documentation, file_name=Path(root.name) / "high_level_documentation")


if __name__ == "__main__":
    generate_documentation()
