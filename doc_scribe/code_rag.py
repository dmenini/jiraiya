import logging
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic_ai import Agent, Tool
from pydantic_ai.models import ModelSettings

from doc_scribe.agent.tools import ToolContext, code_search
from doc_scribe.domain.config import AgentConfig, Config, LLMConfig
from doc_scribe.domain.enums import EncoderName, ModelName
from doc_scribe.settings import Settings
from doc_scribe.code.vectore_store import CodeVectorStore

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


def create_llm_settings(config: LLMConfig) -> ModelSettings:
    return ModelSettings(**config.model_dump())


def create_agent(config: AgentConfig) -> Agent[None, str]:
    search_tool = Tool(
        function=code_search,
        takes_ctx=True,
        name=config.tools.search.name,
        description=config.tools.search.description,
    )
    model = ModelName[config.llm.name]
    return Agent(
        model=model.bedrock_id,
        model_settings=create_llm_settings(config.llm),
        system_prompt=config.prompts.system,
        tools=[search_tool],
        retries=config.retries,
    )


settings = Settings()

config_path = Path(__file__).parent / "agent_config.yaml"
with config_path.open() as fp:
    config = yaml.safe_load(fp)
    config = Config.model_validate(config)

encoder = EncoderName[config.data.encoder]
vectorstore = CodeVectorStore(
    tenant=config.data.tenant,
    dense_encoder=config.data.dense_encoder,
    bm25_encoder=config.data.bm25_encoder,
    late_encoder=config.data.late_encoder,
    host=settings.qdrant_host,
    port=settings.qdrant_port,
)

agent = create_agent(config=config.agent)

tool_context = ToolContext(vectorstore=vectorstore, **config.agent.tools.search.model_dump())

user_prompt = "Generate a Jira ticket description for the following story related to upload-job: Implement progress bar to push updates to the config backend every N steps."
response = agent.run_sync(
    user_prompt=user_prompt,
    deps=tool_context,
)

print(response.output)
