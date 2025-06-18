import hashlib
import json
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance, OptimizersConfigDiff, ScoredPoint, VectorParams
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from doc_scribe.domain.code_data import ClassData, CodeData, MethodData
from doc_scribe.encoder.base import Embeddings

NAMESPACE_UUID = uuid.UUID(int=1984)  # do not change or the hashes will be different


def hash_string_to_uuid(input_string: str) -> uuid.UUID:
    """Hashes a string and returns the corresponding UUID."""
    hash_value = hashlib.sha1(input_string.encode("utf-8")).hexdigest()  # noqa: S324
    return uuid.uuid5(NAMESPACE_UUID, hash_value)


def hash_nested_dict_to_uuid(data: dict[Any, Any]) -> uuid.UUID:
    """Hashes a nested dictionary and returns the corresponding UUID."""
    serialized_data = json.dumps(data, sort_keys=True)
    hash_value = hashlib.sha1(serialized_data.encode("utf-8")).hexdigest()  # noqa: S324
    return uuid.uuid5(NAMESPACE_UUID, hash_value)


def calculate_id(content: str, source: str) -> str:
    """Calculate content and metadata hash."""
    content_hash = str(hash_string_to_uuid(content))
    source_hash = str(hash_string_to_uuid(source))
    return str(hash_string_to_uuid(content_hash + source_hash))


class CodebaseStore:
    def __init__(self, tenant: str, encoder: Embeddings, host: str = "localhost", port: int = 6333) -> None:
        self.encoder = encoder
        self.tenant = tenant
        self.qdrant = QdrantClient(host=host, port=port)

        self.method_collection = f"{tenant}_method"
        self.class_collection = f"{tenant}_class"

        self._ensure_collection(self.method_collection)
        self._ensure_collection(self.class_collection)

    def _ensure_collection(self, name: str) -> None:
        if not self.qdrant.collection_exists(name):
            self.qdrant.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=self.encoder.model.embeddings_size, distance=Distance.COSINE),
                optimizers_config=OptimizersConfigDiff(default_segment_number=1),
                on_disk_payload=True,
            )

    def add(self, data: CodeData) -> None:
        text = data.source_code
        vector = self.encoder.embed_documents([text])[0]

        metadata = data.model_dump(exclude={"source_code", "references"}, mode="json")
        metadata["references"] = json.dumps([ref.model_dump(mode="json") for ref in data.references])
        doc_id = calculate_id(content=text, source=str(data.file_path))

        collection = self.class_collection if isinstance(data, ClassData) else self.method_collection

        point = PointStruct(id=doc_id, vector=vector, payload={"text": text, **metadata})
        self.qdrant.upsert(collection_name=collection, points=[point])

    def _build_filter(self, **filters: Any) -> Filter | None:
        return (
            Filter(must=[FieldCondition(key=key, match=MatchValue(value=value)) for key, value in filters.items()])
            if filters
            else None
        )

    def similarity_search(
        self, query: str, *, top_k: int = 5, is_class: bool = True, **filters: Any
    ) -> list[tuple[CodeData, float]]:
        collection = self.class_collection if is_class else self.method_collection
        query_filter = self._build_filter(**filters)
        vector = self.encoder.embed_query(query)

        result = self.qdrant.query_points(
            collection_name=collection, query_vector=vector, limit=top_k, query_filter=query_filter
        )

        return [self._parse_hit(hit, is_class=is_class) for hit in result.points]

    def keyword_search(
        self,
        keyword: str,
        *,
        top_k: int = 5,
        is_class: bool = True,
        **filters: Any,
    ) -> list[tuple[CodeData, float]]:
        collection = self.class_collection if is_class else self.method_collection
        query_filter = self._build_filter(**filters)

        result = self.qdrant.query_points(
            collection_name=collection,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=False,
            search_params=qdrant_models.SearchParams(hnsw_ef=128, exact=False),
            keyword=keyword,  # This only works if Qdrant is configured for full-text indexing
        )

        return [self._parse_hit(hit, is_class=is_class) for hit in result.points]

    def hybrid_search(
        self,
        query: str,
        keyword: str,
        *,
        alpha: float = 0.5,
        top_k: int = 5,
        is_class: bool = False,
        **filters: Any,
    ) -> list[tuple[CodeData, float]]:
        """Hybrid score = alpha * vector_score + (1 - alpha) * keyword_score"""
        collection = self.class_collection if is_class else self.method_collection
        query_filter = self._build_filter(**filters)
        vector = self.encoder.embed_query(query)

        result = self.qdrant.query_points(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=False,
            score_threshold=None,
            search_params=qdrant_models.SearchParams(hnsw_ef=128, exact=False),
            keyword=keyword,
            using="hybrid",
            with_score=True,
            offset=0,
            score_cutoff=None,
            rerank=alpha,  # Alpha blending between embedding and keyword similarity
        )

        return [self._parse_hit(hit, is_class=is_class) for hit in result.points]

    def _parse_hit(self, hit: ScoredPoint, *, is_class: bool = True) -> tuple[CodeData, float]:
        payload = hit.payload
        refs = json.loads(payload.pop("references", "[]"))
        payload["references"] = [MethodData.model_validate(ref) for ref in refs]

        model_cls = ClassData if is_class else MethodData
        return model_cls.model_validate(payload), hit.score
