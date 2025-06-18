import logging
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import ModelSettings

from doc_scribe.codebase.code_store import CodebaseStore
from doc_scribe.domain.enums import EncoderName, ModelName
from doc_scribe.settings import Settings

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


def create_llm_settings(config: dict) -> ModelSettings:
    return ModelSettings(**config)


def create_agent(config: dict) -> Agent[None, str]:
    model = ModelName[config["llm"]["name"]]
    return Agent(
        model=model.bedrock_id,
        model_settings=create_llm_settings(config["llm"]),
        system_prompt=config["prompts"]["system"],
        retries=1,
    )


settings = Settings()

config_path = Path(__file__).parent / "agent_config.yaml"
with config_path.open() as fp:
    config = yaml.safe_load(fp)

data_config = config["data"]
agent_config = config["agent"]

encoder = EncoderName[data_config["encoder"]]
vectorstore = CodebaseStore(tenant=data_config["tenant"], encoder=encoder, host="localhost", port=6333)

agent = create_agent(config=agent_config)


class CodeSearchArgs(BaseModel):
    query: str
    repo: str | None = None
    class_or_method: Literal["class", "method"] = "class"


class SearchResult(BaseModel):
    file_path: str
    snippet: str


class ToolContext(BaseModel):
    _vectorstore: CodebaseStore
    search_strategy: Literal["hybrid", "similarity", "keyword"]
    top_k: int = 5
    alpha: float = 0.5


@agent.tool(name=agent_config["tools"]["search"]["name"])
def code_search(ctx: RunContext[ToolContext], args: CodeSearchArgs) -> list[SearchResult]:
    """Search in the codebase for classes or methods to be used as context for answering the user question."""
    filters = {}
    if args.repo:
        filters["repo"] = args.repo

    strategy = ctx.deps.search_strategy
    store = ctx.deps._vectorstore
    top_k = ctx.deps.top_k
    alpha = ctx.deps.alpha

    is_class = args.class_or_method == "class"

    if strategy == "similarity":
        hits = store.similarity_search(query=args.query, top_k=top_k, is_class=is_class, **filters)
    elif strategy == "keyword":
        hits = vectorstore.keyword_search(keyword=args.query, top_k=top_k, is_class=is_class, **filters)
    else:
        hits = store.hybrid_search(query=args.query, alpha=alpha, top_k=top_k, is_class=is_class, **filters)

    # Map to output schema
    results = []
    for data, _ in hits:
        results.append(SearchResult(snippet=data.source_code, file_path=str(data.file_path)))

    return results


tool_context = ToolContext(**agent_config["tools"]["search"])
tool_context._vectorstore = vectorstore

user_prompt = ""
response = agent.run_sync(
    user_prompt=user_prompt,
    deps=tool_context,
)

print(response.output)
