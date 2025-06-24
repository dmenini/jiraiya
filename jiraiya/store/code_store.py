import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import Record, ScoredPoint, models
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from jiraiya.domain.data import CodeData, SearchResult, TextData
from jiraiya.store.utils import calculate_id


class CodeVectorStore:
    def __init__(
        self,
        tenant: str,
        code_encoder: str,
        text_encoder: str,
        cache_dir: str | None = None,
        host: str = "localhost",
        port: int = 6333,
    ) -> None:
        self.code_encoder = self._load_model(code_encoder, cache_dir)
        self.text_encoder = self._load_model(text_encoder, cache_dir)

        self.tenant = tenant
        self.qdrant = QdrantClient(host=host, port=port)

        self.collection = f"{tenant}_class"

        self._ensure_collection(self.collection)

    def _load_model(self, model_id: str, cache_dir: str) -> TextEmbedding:
        if cache_dir and Path(cache_dir).is_dir():
            return TextEmbedding(model_id, cache_dir=cache_dir, local_files_only=True)
        return TextEmbedding(model_id, cache_dir=cache_dir)

    def _ensure_collection(self, name: str) -> None:
        if not self.qdrant.collection_exists(name):
            self.qdrant.create_collection(
                collection_name=name,
                vectors_config={
                    "code": models.VectorParams(
                        size=self.code_encoder.embedding_size,
                        distance=models.Distance.COSINE,
                    ),
                    "text": models.VectorParams(
                        size=self.text_encoder.embedding_size,
                        distance=models.Distance.COSINE,
                    ),
                },
            )

    def add_code(self, data: CodeData) -> None:
        code = data.source_code

        metadata = data.model_dump(exclude={"source_code", "references"}, mode="json")
        metadata["references"] = json.dumps([ref.model_dump(mode="json") for ref in data.references])
        doc_id = calculate_id(content="code" + data.name, source=str(data.file_path))

        point = PointStruct(
            id=doc_id,
            vector={"code": next(self.code_encoder.passage_embed([code]))},
            payload={"text": code, **metadata},
        )
        self.qdrant.upsert(collection_name=self.collection, points=[point])

    def add_text(self, data: TextData) -> None:
        text = data.text
        metadata = data.model_dump(exclude={"source_code"}, mode="json")

        # Unique id per name and file path of docs
        doc_id = calculate_id(content="text" + data.name, source=str(data.file_path))

        point = PointStruct(
            id=doc_id,
            vector={"text": next(self.text_encoder.passage_embed([text]))},
            payload={"text": text, **metadata},
        )
        self.qdrant.upsert(collection_name=self.collection, points=[point])

    def clear(self) -> None:
        self.qdrant.delete_collection(collection_name=self.collection)
        self._ensure_collection(self.collection)

    def _build_filter(self, **filters: Any) -> Filter | None:
        return (
            Filter(must=[FieldCondition(key=key, match=MatchValue(value=value)) for key, value in filters.items()])
            if filters
            else None
        )

    def similarity_search(self, query: str, *, top_k: int = 5, **filters: Any) -> list[SearchResult]:
        query_filter = self._build_filter(**filters)
        code_vector = next(self.code_encoder.query_embed(query))
        text_vector = next(self.text_encoder.query_embed(query))

        responses = self.qdrant.query_batch_points(
            collection_name=self.collection,
            requests=[
                models.QueryRequest(
                    query=text_vector,
                    using="text",
                    with_payload=True,
                    limit=top_k,
                    filter=query_filter,
                ),
                models.QueryRequest(
                    query=code_vector,
                    using="code",
                    with_payload=True,
                    limit=top_k,
                    filter=query_filter,
                ),
            ],
        )

        results = [hit for response in responses for hit in response.points]
        return [self._parse_hit(hit) for hit in results]

    def _parse_hit(self, hit: ScoredPoint | Record) -> SearchResult:
        payload = hit.payload

        return SearchResult(
            file_path=payload["file_path"],
            repo=payload["repo"],
            name=payload["name"],
            text=payload.get("text") or payload.get("source_code"),
            score=hit.score if isinstance(hit, ScoredPoint) else 1.0,
        )

    def find(
        self,
        *,
        limit: int = 10,
        **filters: Any,
    ) -> Iterator[SearchResult]:
        scroll_filter = self._build_filter(**filters)
        offset = 0

        while True:
            response, next_page_offset = self.qdrant.scroll(
                self.collection,
                limit=limit,
                offset=offset,
                scroll_filter=scroll_filter,
            )

            if not response:
                break

            for hit in response:
                yield self._parse_hit(hit)

            offset = next_page_offset

            if not offset:
                break

    def get_all_repos(self, batch_size: int = 100) -> list[str]:
        unique_repos = set()

        for res in self.find(limit=batch_size):
            unique_repos.add(res.repo)

        return list(unique_repos)

    def count(self) -> int:
        result = self.qdrant.count(self.collection)
        return result.count
