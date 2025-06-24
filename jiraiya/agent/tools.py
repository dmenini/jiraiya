import logging
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext

from jiraiya.domain.data import SearchResult
from jiraiya.domain.jira import JiraIssueOutput
from jiraiya.io.jira_ticket_manager import JiraIssueManager
from jiraiya.store.code_store import CodeVectorStore

log = logging.getLogger(__name__)


class CodeSearchArgs(BaseModel):
    query: str = Field(description="Search query")
    repo: str | None = Field(default=None, description="Repository slug for filtering search results")


class SearchToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    vectorstore: CodeVectorStore
    search_strategy: Literal["hybrid", "similarity", "keyword"] = "similarity"
    top_k: int = 5


def code_search(ctx: RunContext[SearchToolContext], args: CodeSearchArgs) -> list[SearchResult]:
    """Search in the codebase for classes or methods to be used as context for answering the user question."""
    filters = {}
    if args.repo:
        filters["repo"] = args.repo

    store = ctx.deps.vectorstore
    top_k = ctx.deps.top_k

    results = store.similarity_search(query=args.query, top_k=top_k, **filters)
    log.info("Found %d results for search query '%s' (repo=%s)", len(results), args.query, args.repo)
    return results


class IssueCreateArgs(BaseModel):
    summary: str = Field(description="Issue title")
    description: str = Field(description="Detailed issue description")
    issue_type: Literal["Story", "Task", "Bug"] = Field(default="Story", description="Issue type")
    epic_key: str | None = Field(default=None, description="Epic key, must be explicitly provided by the user")


class JiraToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    jira_client: JiraIssueManager
    project_key: str
    agile_object: str


def create_jira_ticket(ctx: RunContext[JiraToolContext], args: IssueCreateArgs) -> JiraIssueOutput:
    """Create a jira ticket."""

    # TODO: Connect this to Jira
    client = ctx.deps.jira_client
    log.info("Created Jira ticket")

    return JiraIssueOutput(**args.model_dump(), key=str(uuid.uuid4()), status="CREATED")


class ToolContext(SearchToolContext, JiraToolContext):
    pass
