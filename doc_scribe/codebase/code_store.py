import hashlib
import json
import uuid
from typing import Any

from chromadb import PersistentClient

from doc_scribe.domain.code_data import ClassData, CodeData, MethodData

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
    _hash = str(hash_string_to_uuid(content_hash + source_hash))
    return _hash


class CodebaseStore:
    def __init__(self, tenant: str):
        self.chroma_client = PersistentClient(path=".db", tenant=tenant)

        self.method_collection = self.chroma_client.get_or_create_collection(name="method")
        self.class_collection = self.chroma_client.get_or_create_collection(name="class")

    def add(self, data: CodeData, text: str, vector: list[float]) -> None:
        metadata = data.model_dump(exclude={"source_code", "references"}, mode="json")
        metadata["references"] = json.dumps([ref.model_dump_json() for ref in data.references])

        if isinstance(data, ClassData):
            self.class_collection.upsert(
                ids=[calculate_id(content=text, source=str(data.file_path))],
                embeddings=[vector],
                documents=[text],
                metadatas=[metadata],
            )
        elif isinstance(data, MethodData):
            self.method_collection.upsert(
                ids=[calculate_id(content=text, source=str(data.file_path))],
                embeddings=[vector],
                documents=[text],
                metadatas=[metadata],
            )
