from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext

from doc_scribe.domain.data import SearchResult
from doc_scribe.store.code_store import CodeVectorStore


class CodeSearchArgs(BaseModel):
    query: str = Field(description="Search query")
    repo: str | None = Field(default=None, description="Optional filter to limit the search to a specific repo")


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    vectorstore: CodeVectorStore
    search_strategy: Literal["hybrid", "similarity", "keyword"] = "similarity"
    top_k: int = 5


def code_search(ctx: RunContext[ToolContext], args: CodeSearchArgs) -> list[SearchResult]:
    """Search in the codebase for classes or methods to be used as context for answering the user question."""
    filters = {}
    if args.repo:
        filters["repo"] = args.repo

    store = ctx.deps.vectorstore
    top_k = ctx.deps.top_k

    return store.similarity_search(query=args.query, top_k=top_k, **filters)


def get_all_repos(ctx: RunContext[ToolContext]) -> list[str]:
    """Get a list of all repo names stored in the vectorstore."""
    store = ctx.deps.vectorstore
    return store.get_all_repos()
