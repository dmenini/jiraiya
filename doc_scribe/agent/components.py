from pydantic_ai import Agent, Tool
from pydantic_ai.settings import ModelSettings

from doc_scribe.agent.tools import code_search, create_jira_ticket
from doc_scribe.domain.config import AgentConfig, LLMConfig
from doc_scribe.domain.documentation import TechnicalDoc
from doc_scribe.domain.enums import ModelName


def create_llm_settings(config: LLMConfig) -> ModelSettings:
    return ModelSettings(**config.model_dump())


def create_docs_writer(config: AgentConfig) -> Agent[None, TechnicalDoc]:
    model = ModelName[config.llm.name]
    return Agent(
        model=model.bedrock_id,
        model_settings=create_llm_settings(config.llm),
        system_prompt=config.prompts.writer,
        output_type=TechnicalDoc,
        retries=config.retries,
    )


def create_agent(config: AgentConfig) -> Agent[None, str]:
    search_tool = Tool(
        function=code_search,
        takes_ctx=True,
        name=config.tools.search.name,
        description=config.tools.search.description,
    )
    jira_tool = Tool(
        function=create_jira_ticket,
        takes_ctx=True,
        name=config.tools.jira.name,
        description=config.tools.jira.description,
    )
    model = ModelName[config.llm.name]
    return Agent(
        model=model.bedrock_id,
        model_settings=create_llm_settings(config.llm),
        system_prompt=config.prompts.system,
        tools=[search_tool, jira_tool],
        retries=config.retries,
    )
