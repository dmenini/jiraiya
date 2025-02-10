from pathlib import Path

from anthropic import AsyncAnthropicBedrock
from pydantic_ai.agent import Agent
from pydantic_ai.models import Model, ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

from code_analyzer.domain.enums import ModelName
from code_analyzer.io.loader import CodebaseLoader
from code_analyzer.prompts.human_prompts import (
    AUDITOR_PROMPT, FOLLOWUP_WRITER_PROMPT, INTEGRATION_PROMPT, WRITER_PROMPT,
)
from code_analyzer.prompts.system_prompt import (
    WRITER_SYSTEM_PROMPT, AUDITOR_SYSTEM_PROMPT,
    INTEGRATOR_SYSTEM_PROMPT,
)
from code_analyzer.settings import Settings

CODE_SEPARATOR = "\n\n==================================\n\n"


def write_output(data: str, file_name: str) -> None:
    output_file = (Path("output") / file_name).with_suffix(".md")
    with output_file.open("w") as fp:
        fp.write(data)


def read_output(file_name: str) -> str:
    output_file = (Path("output") / file_name).with_suffix(".md")
    with output_file.open("r") as fp:
        return fp.read()


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


def create_writer_agent(llm: Model, settings: Settings) -> Agent:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=WRITER_SYSTEM_PROMPT,
        result_type=str,
    )


def create_auditor_agent(llm: Model, settings: Settings) -> Agent:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=AUDITOR_SYSTEM_PROMPT,
        result_type=str,
    )


def create_integrator_agent(llm: Model, settings: Settings) -> Agent:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=INTEGRATOR_SYSTEM_PROMPT,
        result_type=str,
    )


def generate_docs_for_codebase(loader: CodebaseLoader, writer: Agent, auditor: Agent, output_key: str) -> str:
    print(output_key.upper())
    tree = loader.load_all_files()

    all_files = list(tree.keys())
    structure = "\n".join(all_files)
    print(structure)

    sections = [f"Filename: {file}\n\n{code}" for file, code in tree.items()]
    codebase = CODE_SEPARATOR.join(sections)

    # Generate first iteration of docs
    user_input = WRITER_PROMPT.format(structure=structure, codebase=codebase)
    response = writer.run_sync(user_prompt=user_input)
    documentation = response.data
    history = response.new_messages()

    feedback = generate_feedback(loader, auditor, documentation=documentation)

    # Include the feedback and generate a second iteration of docs
    user_input = FOLLOWUP_WRITER_PROMPT.format(feedback=feedback)
    response = writer.run_sync(user_prompt=user_input, message_history=history)
    documentation = response.data

    # Write documentation to file
    write_output(documentation, file_name=str(loader.root_path.name) + "_" + output_key)

    return documentation


def generate_feedback(loader: CodebaseLoader, auditor: Agent, documentation: str) -> str:
    # Provide a feedback for the generated docs
    tree = loader.load_all_files()
    sections = [f"Filename: {file}\n\n{code}" for file, code in tree.items()]
    codebase = CODE_SEPARATOR.join(sections)

    user_input = AUDITOR_PROMPT.format(codebase=codebase, docs=documentation)
    response = auditor.run_sync(user_prompt=user_input)
    feedback = response.data

    print(feedback)

    return feedback


def generate_documentation() -> None:
    root = Path("/Users/taamedag/Desktop/cai/aaas/chat-api/chat_api")
    exclude = ["prompts"]
    sections = {
        "generic": [],
        "controller": ["routes", "security"],
        "service": ["agents", "chat", "memory"],
        "repository": ["repository"],
        "extra": ["api", "models"],
    }

    settings = Settings()
    llm = create_llm(settings, ModelName.CLAUDE_3_5_SONNET)
    writer_agent = create_writer_agent(llm, settings)

    llm = create_llm(settings, ModelName.CLAUDE_3_SONNET)
    auditor_agent = create_auditor_agent(llm, settings)

    llm = create_llm(settings, ModelName.CLAUDE_3_5_SONNET)
    integrator_agent = create_integrator_agent(llm, settings)

    docs = {}
    for key, includes in sections.items():
        loader = CodebaseLoader(root_path=root, exclude=exclude, include=includes)
        doc = generate_docs_for_codebase(loader, writer=writer_agent, auditor=auditor_agent, output_key=key)
        # doc = read_output(file_name=str(loader.root_path.name) + "_" + key)

        docs[key] = doc

    # Integrate the previous docs into a final documentation
    final = docs.pop("generic")
    for key, doc in docs.items():
        user_input = INTEGRATION_PROMPT.format(documentation=final, key=key, section_detail=doc)
        response = integrator_agent.run_sync(user_prompt=user_input)

        final = response.data
        write_output(final, file_name=str(root.name))


if __name__ == "__main__":
    generate_documentation()
