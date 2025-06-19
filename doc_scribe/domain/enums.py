from enum import Enum


class ModelName(Enum):
    CLAUDE_3_SONNET = ("CLAUDE_3_SONNET", "bedrock:anthropic.claude-3-sonnet-20240229-v1:0")
    CLAUDE_3_HAIKU = ("CLAUDE_3_HAIKU", "bedrock:anthropic.claude-3-haiku-20240307-v1:0")
    CLAUDE_3_5_SONNET = ("CLAUDE_3_5_SONNET", "bedrock:anthropic.claude-3-5-sonnet-20240620-v1:0")
    CLAUDE_3_7_SONNET = ("CLAUDE_3_7_SONNET", "bedrock:anthropic.claude-3-7-sonnet-20250219-v1:0")

    def __init__(self, name: str, bedrock_id: str) -> None:
        self._name = name
        self._bedrock_id = bedrock_id

    @property
    def value(self) -> str:  # type: ignore[override]
        return self._name

    @property
    def bedrock_id(self) -> str:
        """Large Language Model ID according to Amazon Bedrock API."""
        return self._bedrock_id


class EncoderName(Enum):
    TITAN_V1 = (
        "TITAN_V1",
        "amazon.titan-embed-text-v1",
        1536,
        48_000,
    )
    COHERE_V3 = (
        "COHERE_V3",
        "cohere.embed-multilingual-v3",
        1024,
        2024,
    )

    def __init__(self, name: str, bedrock_id: str, embeddings_size: int, max_chars: int) -> None:
        self._name = name
        self._bedrock_id = bedrock_id
        self._embeddings_size = embeddings_size
        self._max_chars = max_chars

    @property
    def value(self) -> str:
        return self._name

    @property
    def bedrock_id(self) -> str:
        """Embeddings Model ID according to Amazon Bedrock API."""
        return self._bedrock_id

    @property
    def embedding_size(self) -> int:
        """Number of dimensions for embedding vectors."""
        return self._embeddings_size

    @property
    def max_chars(self) -> int:
        """Maximum number of chars that can be encoded. It directly limits the max allowed
        chunk size. It should be much less than the context window of the model, since if
        the text is too long the embeddings quality is affected.
        """
        return self._max_chars
