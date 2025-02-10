from enum import Enum


class ModelName(Enum):
    CLAUDE_3_SONNET = ("CLAUDE_3_SONNET", "anthropic.claude-3-sonnet-20240229-v1:0")
    CLAUDE_3_HAIKU = ("CLAUDE_3_HAIKU", "anthropic.claude-3-haiku-20240307-v1:0")
    CLAUDE_3_5_SONNET = ("CLAUDE_3_5_SONNET", "anthropic.claude-3-5-sonnet-20240620-v1:0")

    def __init__(self, name: str, bedrock_id: str) -> None:
        self._name = name
        self._bedrock_id = bedrock_id

    @property
    def value(self) -> str:
        return self._name

    @property
    def bedrock_id(self) -> str:
        """Large Language Model ID according to Amazon Bedrock API."""
        return self._bedrock_id
