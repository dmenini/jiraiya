import os
from json import JSONDecodeError
from typing import Any

from jira import JIRA

from doc_scribe.domain.jira import JiraIssue, JiraIssueOutput


class JiraIssueManager:
    def __init__(self, server: str, token: str):
        self.jira = None

    def create_issue(self, ticket: JiraIssue) -> str:
        fields: dict[str, Any] = {
            "project": {"key": ticket.project_key},
            "summary": ticket.summary,
            "description": ticket.description,
            "issuetype": {"name": ticket.issue_type},
        }

        # Handle agile custom fields
        if ticket.agile.epic_key:
            fields["customfield_10014"] = ticket.agile.epic_key
        if ticket.agile.story_points is not None:
            fields["customfield_10020"] = ticket.agile.story_points
        if ticket.agile.sprint_id is not None:
            fields["customfield_10007"] = ticket.agile.sprint_id
        if ticket.agile.priority:
            fields["priority"] = {"name": ticket.agile.priority}
        if ticket.agile.labels:
            fields["labels"] = ticket.agile.labels

        issue = self.jira.create_issue(fields=fields)
        return issue.key

    def get_issue(self, ticket_key: str) -> JiraIssueOutput:
        try:
            issue = self.jira.issue(ticket_key)
        except JSONDecodeError:
            raise ConnectionError("Error with server response")

        return JiraIssueOutput(
            key=issue.key,
            project_key=issue.fields.project.name if issue.fields.project else "",
            summary=issue.fields.summary,
            description=issue.fields.description,
            issue_type=issue.fields.issuetype.name,
            status=issue.fields.status.name,
            assignee=issue.fields.assignee.displayName if issue.fields.assignee else None,
            reporter=issue.fields.reporter.displayName if issue.fields.reporter else None,
            agile_object=getattr(issue.fields, "customfield_25851", None),
            epic_key=getattr(issue.fields, "customfield_12150", None),
            story_points=getattr(issue.fields, "customfield_10263", None),
            labels=issue.fields.labels or [],
        )

    def update_ticket(self, ticket_key: str, updated_fields: dict[str, Any]) -> None:
        issue = self.jira.issue(ticket_key)
        issue.update(fields=updated_fields)

    def add_comment(self, ticket_key: str, comment: str) -> None:
        self.jira.add_comment(ticket_key, comment)


if __name__ == "__main__":
    manager = JiraIssueManager(
        server="https://jira.swisscom.com",
        token=os.getenv("JIRA_TOKEN"),
    )

    ticket = manager.get_issue("PLATO-19326")
    print(ticket)
