from pydantic import BaseModel


class DataConfig(BaseModel):
    tenant: str
    dense_encoder: str = "sentence-transformers/all-MiniLM-L6-v2"
    code_encoder: str = "jinaai/jina-embeddings-v2-base-code"
    bm25_encoder: str = "Qdrant/bm25"
    late_encoder: str = "jinaai/jina-colbert-v2"
    codebases: list[str]
    blacklist: list[str] = []
    reset: bool = False
    cache_dir: str | None = None


# TODO: split this config
class ToolConfig(BaseModel):
    name: str
    description: str
    search_strategy: str = "similarity"
    top_k: int = 5
    project_key: str = ""
    agile_object: str = ""


class ToolsConfig(BaseModel):
    search: ToolConfig
    jira: ToolConfig | None = None


class LLMConfig(BaseModel):
    name: str
    temperature: float
    max_tokens: int | None = None
    top_p: float | None = None


class PromptsConfig(BaseModel):
    system: str
    writer: str = ""


class AgentConfig(BaseModel):
    retries: int
    llm: LLMConfig
    tools: ToolsConfig
    prompts: PromptsConfig


class Config(BaseModel):
    data: DataConfig
    agent: AgentConfig
