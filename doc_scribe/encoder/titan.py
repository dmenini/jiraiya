import logging
import os

from doc_scribe.encoder.base import Embeddings

log = logging.getLogger(__name__)


class TitanEmbeddings(Embeddings):
    def _embed_query(self, text: str) -> list[float]:
        # Replace newlines, which can negatively affect performance.
        text = text.replace(os.linesep, " ")

        response_body = self._invoke_model(input_body={"inputText": text})
        return response_body.get("embedding", [])

    def _embed_document(self, text: str) -> list[float]:
        return self._embed_query(text)
