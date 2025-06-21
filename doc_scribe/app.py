import logging
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from doc_scribe.agent.components import create_agent
from doc_scribe.agent.tools import ToolContext
from doc_scribe.domain.config import Config
from doc_scribe.settings import Settings
from doc_scribe.store.code_store import CodeVectorStore

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

settings = Settings()

config_path = Path(__file__).parent / "agent_config.yaml"
with config_path.open() as fp:
    config = yaml.safe_load(fp)
    config = Config.model_validate(config)

vectorstore = CodeVectorStore(
    tenant=config.data.tenant,
    code_encoder=config.data.code_encoder,
    text_encoder=config.data.dense_encoder,
    host=settings.qdrant_host,
    port=settings.qdrant_port,
)

agent = create_agent(config=config.agent)

tool_context = ToolContext(vectorstore=vectorstore, **config.agent.tools.search.model_dump())

user_prompt = "What are the routes in knowledge manager?"
response = agent.run_sync(
    user_prompt=user_prompt,
    deps=tool_context,
)

print(response.output)
