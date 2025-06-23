from typing import Literal

from pydantic import BaseModel


class JiraIssue(BaseModel):
    project_key: str
    summary: str
    description: str
    issue_type: Literal["Story", "Task", "Bug"] = "Story"
    agile_object: list[str] = []
    epic_key: str | None = None
    story_points: float | None = None
    labels: list[str] | None = None


class JiraIssueOutput(JiraIssue):
    key: str
    status: str
    assignee: str | None = None
    reporter: str | None = None
