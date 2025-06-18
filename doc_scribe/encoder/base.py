import json
import logging
from typing import Any

import boto3
import numpy as np

from doc_scribe.domain.enums import EncoderName

log = logging.getLogger(__name__)


class Embeddings:
    def __init__(self, model: EncoderName, *, normalize: bool = True, **kwargs: Any) -> None:
        self.model = model
        self.normalize = normalize
        self.model_kwargs = kwargs

        self.client = boto3.Session().client("bedrock-runtime")

    def _embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    def _embed_document(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        """Compute query embeddings using a Bedrock model."""
        embedding = self._embed_query(text)

        if self.normalize:
            return self._normalize_vectors([embedding])[0]

        return embedding

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Compute document embeddings using a Bedrock model."""
        embeddings = []
        for text in texts:
            if len(text) > self.model.max_chars:
                log.warning(
                    "Text is longer (%s)than what is supported by the embeddings model " "(%s): cropping it",
                    len(text),
                    self.model.max_chars,
                )
                cropped = text[: self.model.max_chars]
                emb = self._embed_document(cropped)
            else:
                emb = self._embed_document(text)

            embeddings.append(emb)

        if self.normalize:
            return self._normalize_vectors(embeddings)

        return embeddings

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

    def _normalize_vectors(self, embeddings: list[list[float]]) -> list[list[float]]:
        """Normalize a list of embedding vectors to unit vectors."""
        emb = np.array(embeddings)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized = emb / norms
        return normalized.tolist()
