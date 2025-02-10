from pathlib import Path

from anthropic import AsyncAnthropicBedrock
from pydantic_ai.agent import Agent
from pydantic_ai.models import Model, ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

from code_analyzer.domain.enums import ModelName
from code_analyzer.io.loader import CodebaseLoader
from code_analyzer.prompts.human_prompts import (
    DEVELOPER_PROMPT, FINAL_PROMPT, FIRST_ANALYZER_PROMPT,
    FOLLOWUP_ANALYZER_PROMPT,
)
from code_analyzer.prompts.system_prompt import (
    ANALYZER_SYSTEM_PROMPT, DEVELOPER_SYSTEM_PROMPT,
    FINALIZATION_SYSTEM_PROMPT,
)
from code_analyzer.settings import Settings

CODE_SEPARATOR = "\n\n==================================\n\n"
NUM_ITERATIONS = 3


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


def create_analyzer_agent(llm: Model, settings: Settings) -> Agent:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=ANALYZER_SYSTEM_PROMPT,
        result_type=str,
    )


def create_developer_agent(llm: Model, settings: Settings) -> Agent:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=DEVELOPER_SYSTEM_PROMPT,
        result_type=str,
    )


def create_finalizer_agent(llm: Model, settings: Settings) -> Agent:
    return Agent(
        model=llm,
        model_settings=create_llm_settings(settings),
        system_prompt=FINALIZATION_SYSTEM_PROMPT,
        result_type=str,
    )


def generate_docs_for_codebase(loader: CodebaseLoader, analyzer_agent: Agent, developer_agent: Agent,
                               output_key: str) -> str:
    print(output_key.upper())
    tree = loader.load_all_files()

    all_files = list(tree.keys())
    structure = "\n".join(all_files)
    print(structure)

    sections = [f"Filename: {file}\n\n{code}" for file, code in tree.items()]
    codebase = CODE_SEPARATOR.join(sections)

    # Generate first iteration of docs
    user_input = FIRST_ANALYZER_PROMPT.format(structure=structure, codebase=codebase)
    response = analyzer_agent.run_sync(user_prompt=user_input)
    docs = response.data
    history = response.new_messages()

    # Provide a feedback for the generated docs
    user_input = DEVELOPER_PROMPT.format(codebase=codebase, docs=docs)
    response = developer_agent.run_sync(user_prompt=user_input)
    feedback = response.data

    print(feedback)

    # Include the feedback and generate a second iteration of docs
    user_input = FOLLOWUP_ANALYZER_PROMPT.format(feedback=feedback)
    response = analyzer_agent.run_sync(user_prompt=user_input, message_history=history)
    docs = response.data

    # Write documentation to file
    write_output(docs, file_name=str(loader.root_path.name) + "_" + output_key)

    return docs


def generate_documentation() -> None:
    root = Path("/Users/taamedag/Desktop/cai/aaas/chat-api/chat_api")
    exclude = ["prompts"]
    sections = {
        "generic": [],
        "controller": ["routes", "security", "app", "dependencies"],
        "service": ["agents", "chat", "memory"],
        "repository": ["repository"],
        "models": ["models"],
        "api": ["api"],
    }

    settings = Settings()
    llm = create_llm(settings, ModelName.CLAUDE_3_5_SONNET)
    analyzer_agent = create_analyzer_agent(llm, settings)

    llm = create_llm(settings, ModelName.CLAUDE_3_SONNET)
    developer_agent = create_developer_agent(llm, settings)

    llm = create_llm(settings, ModelName.CLAUDE_3_5_SONNET)
    finalizer_agent = create_finalizer_agent(llm, settings)

    # generic_docs = read_output(str(root.name) + "_generic")
    # repository_docs = read_output(str(root.name) + "_repository")
    # service_docs = read_output(str(root.name) + "_service")
    # routes_docs = read_output(str(root.name) + "_routes")

    docs = {}
    for key, includes in sections.items():
        loader = CodebaseLoader(root_path=root, exclude=exclude, include=includes)
        doc = generate_docs_for_codebase(loader, analyzer_agent, developer_agent, output_key=key)
        docs[key] = doc

    # Integrate the previous docs into a final documentation
    final = docs.pop("generic")
    for key, doc in docs.items():
        docs = f"Documentation:\n\n{final}{CODE_SEPARATOR}Documentation for {key}\n\n{doc}"

        user_input = FINAL_PROMPT.format(docs=docs)
        response = finalizer_agent.run_sync(user_prompt=user_input)

        final = response.data
        write_output(final, file_name=str(root.name))


if __name__ == "__main__":
    generate_documentation()
