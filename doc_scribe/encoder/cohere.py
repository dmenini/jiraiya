import os
from typing import Literal

from doc_scribe.encoder.base import Embeddings


class CohereEmbeddings(Embeddings):
    def _embed(self, text: str, input_type: Literal["search_query", "search_document"]) -> list[float]:
        # Replace newlines, which can negatively affect performance.
        text = text.replace(os.linesep, " ")

        response_body = self._invoke_model(input_body={"input_type": input_type, "texts": [text]})
        embeddings = response_body.get("embeddings")

        if not embeddings:
            msg = "Something went wrong: no embeddings computed for the given input text"
            raise ValueError(msg)

        return embeddings[0]

    def _embed_query(self, text: str) -> list[float]:
        return self._embed(text=text, input_type="search_query")

    def _embed_document(self, text: str) -> list[float]:
        return self._embed(text=text, input_type="search_document")
