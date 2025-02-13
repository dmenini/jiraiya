from pydantic_ai.agent import Agent

from code_analyzer.domain.documentation import TechnicalDoc
from code_analyzer.io.code_loader import CodebaseLoader
from code_analyzer.io.markdown import convert_json_to_md, write_md
from code_analyzer.prompts.human_prompts import AUDITOR_PROMPT, FOLLOWUP_WRITER_PROMPT, WRITER_PROMPT

CODE_SEPARATOR = "\n\n==================================\n\n"


def generate_docs_for_file(code: str, writer: Agent[None, TechnicalDoc]) -> TechnicalDoc:
    response = writer.run_sync(user_prompt=code)
    documentation = response.data
    return documentation


def generate_docs_for_module(module: str, file_docs: dict[str, TechnicalDoc], writer: Agent) -> TechnicalDoc:
    print(f"Processing {module}")
    keys = [key for key in file_docs.keys() if key.startswith(module)]

    if len(keys) == 1:
        documentation = file_docs[keys[0]]
        return documentation

    module_documentation = f"Join the following technical docs for the files in module {module} into a standalone document respecting the provided json schema.\n\n"
    for key in keys:
        file_doc = convert_json_to_md({key: file_docs[key]})
        module_documentation += f"**File: {key}**\n{file_doc}\n\n---\n\n"

    response = writer.run_sync(user_prompt=module_documentation)
    documentation = response.data
    write_md(documentation, file_name=module)

    return documentation


def generate_docs_for_codebase(loader: CodebaseLoader, writer: Agent, file_name: str) -> str:
    print(file_name.upper())
    tree = loader.load_all_files()

    all_files = list(tree.keys())
    structure = "\n".join(all_files)
    print(structure)

    sections = [f"**File: {file}**\n{code}\n\n---\n\n" for file, code in tree.items()]
    codebase = CODE_SEPARATOR.join(sections)

    user_input = WRITER_PROMPT.format(structure=structure, codebase=codebase)
    response = writer.run_sync(user_prompt=user_input)
    documentation = response.data

    # Write documentation to file
    write_md(documentation, file_name=file_name)

    return documentation


def generate_docs_for_codebase_with_feedback(
    loader: CodebaseLoader, writer: Agent, auditor: Agent, output_key: str
) -> str:
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
    write_md(documentation, file_name=str(loader.root_path.name) + "_" + output_key)

    return documentation


def generate_feedback(loader: CodebaseLoader, auditor: Agent, documentation: str) -> str:
    # Provide a feedback for the generated docs
    tree = loader.load_all_files()
    sections = [f"Filename: {file}\n\n{code}" for file, code in tree.items()]
    codebase = CODE_SEPARATOR.join(sections)

    user_input = AUDITOR_PROMPT.format(codebase=codebase, docs=documentation)
    response = auditor.run_sync(user_prompt=user_input)
    feedback = response.data

    return feedback
