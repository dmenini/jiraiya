import json
import logging
import os
from collections.abc import Iterable
from typing import Any, Literal

import boto3
import numpy as np
from fastembed.common.types import NumpyArray
from fastembed.text.text_embedding_base import TextEmbeddingBase

from doc_scribe.domain.enums import EncoderName

log = logging.getLogger(__name__)


class BedrockEmbeddings(TextEmbeddingBase):
    def __init__(self, model_name: str, *, normalize: bool = True, **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)
        self.model = EncoderName[model_name]
        self.normalize = normalize

        self.client = boto3.Session().client("bedrock-runtime")

    def embed(
        self,
        documents: str | Iterable[str],
        batch_size: int = 256,  # noqa: ARG002
        parallel: int | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> Iterable[NumpyArray]:
        if isinstance(documents, str):
            embedding = self._embed_query(documents)
            if self.normalize:
                yield self._normalize_vectors([embedding])[0]
            else:
                yield np.array(embedding)
        else:
            for q in documents:
                embedding = self._embed_query(q)
                if self.normalize:
                    yield self._normalize_vectors([embedding])[0]
                else:
                    yield np.array(embedding)

    def passage_embed(self, texts: Iterable[str], **kwargs: Any) -> Iterable[NumpyArray]:  # noqa: ARG002
        """Compute document embeddings using a Bedrock model."""
        for text in texts:
            if len(text) > self.model.max_chars:
                log.warning(
                    "Text is longer (%s)than what is supported by the embeddings model " "(%s): cropping it",
                    len(text),
                    self.model.max_chars,
                )
                cropped = text[: self.model.max_chars]
                embedding = self._embed_document(cropped)
            else:
                embedding = self._embed_document(text)

            if self.normalize:
                yield self._normalize_vectors([embedding])[0]
            else:
                yield np.array(embedding)

    def _invoke_model(self, input_body: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(input_body)

        response = self.client.invoke_model(
            body=body,
            modelId=self.model.bedrock_id,
            accept="application/json",
            contentType="application/json",
        )
        data = response.get("body").read()

        return json.loads(data)

    def _normalize_vectors(self, embeddings: list[list[float]]) -> list[NumpyArray]:
        """Normalize a list of embedding vectors to unit vectors."""
        emb = np.array(embeddings)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return emb / norms

    def _cohere_embed(self, text: str, input_type: Literal["search_query", "search_document"]) -> list[float]:
        # Replace newlines, which can negatively affect performance.
        text = text.replace(os.linesep, " ")

        response_body = self._invoke_model(input_body={"input_type": input_type, "texts": [text]})
        embeddings = response_body.get("embeddings")

        if not embeddings:
            msg = "Something went wrong: no embeddings computed for the given input text"
            raise ValueError(msg)

        return embeddings[0]

    def _embed_query(self, text: str) -> list[float]:
        # Replace newlines, which can negatively affect performance.
        text = text.replace(os.linesep, " ")

        if self.model == EncoderName.COHERE_V3:
            return self._cohere_embed(text=text, input_type="search_query")

        response_body = self._invoke_model(input_body={"inputText": text})
        return response_body.get("embedding", [])

    def _embed_document(self, text: str) -> list[float]:
        if self.model == EncoderName.COHERE_V3:
            return self._cohere_embed(text=text, input_type="search_document")

        return self._embed_query(text)

    @classmethod
    def get_embedding_size(cls, model_name: str) -> int:
        """Returns embedding size of the passed model."""
        return EncoderName[model_name].embedding_size

    @property
    def embedding_size(self) -> int:
        """Returns embedding size for the current model"""
        return EncoderName[self.model_name].embedding_size
