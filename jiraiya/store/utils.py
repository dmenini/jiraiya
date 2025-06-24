import hashlib
import json
import uuid
from typing import Any

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
