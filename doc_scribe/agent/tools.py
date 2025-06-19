from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext

from doc_scribe.codebase.code_store import CodebaseStore


class CodeSearchArgs(BaseModel):
    query: str = Field(description="Search query")
    repo: str | None = Field(default=None, description="Optional filter to limit the search to a specific repo")


class SearchResult(BaseModel):
    file_path: str
    snippet: str


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    vectorstore: CodebaseStore
    search_strategy: Literal["hybrid", "similarity", "keyword"]
    top_k: int = 5
    high_level: bool = True


# TODO: Have 2 tools? I high level (class), and one low level (method)


def code_search(ctx: RunContext[ToolContext], args: CodeSearchArgs) -> list[SearchResult]:
    """Search in the codebase for classes or methods to be used as context for answering the user question."""
    filters = {}
    if args.repo:
        filters["repo"] = args.repo

    strategy = ctx.deps.search_strategy
    store = ctx.deps.vectorstore
    top_k = ctx.deps.top_k
    is_class = ctx.deps.high_level

    if strategy == "similarity":
        hits = store.similarity_search(query=args.query, top_k=top_k, is_class=is_class, **filters)
    elif strategy == "keyword":
        hits = store.keyword_search(keyword=args.query, top_k=top_k, is_class=is_class, **filters)
    else:
        hits = store.hybrid_search(query=args.query, top_k=top_k, is_class=is_class, **filters)

    # Map to output schema
    results = []
    for data, _ in hits:
        results.append(SearchResult(snippet=data.source_code, file_path=str(data.file_path)))

    return results
