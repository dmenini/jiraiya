from pydantic import BaseModel


class DataConfig(BaseModel):
    tenant: str
    dense_encoder: str
    bm25_encoder: str
    late_encoder: str
    codebases: list[str]
    blacklist: list[str]


class ToolConfig(BaseModel):
    name: str
    description: str
    search_strategy: str
    top_k: int


class ToolsConfig(BaseModel):
    search: ToolConfig


class LLMConfig(BaseModel):
    name: str
    temperature: float
    max_tokens: int | None = None
    top_p: float | None = None


class PromptsConfig(BaseModel):
    system: str


class AgentConfig(BaseModel):
    retries: int
    llm: LLMConfig
    tools: ToolsConfig
    prompts: PromptsConfig


class Config(BaseModel):
    data: DataConfig
    agent: AgentConfig
