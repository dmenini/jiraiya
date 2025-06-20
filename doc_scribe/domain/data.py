from enum import Enum
from pathlib import Path

from pydantic import BaseModel, computed_field


class ReferenceType(Enum):
    IMPORT = "IMPORT"
    FROM_IMPORT = "FROM_IMPORT"
    USAGE = "USAGE"
    INSTANTIATION = "INSTANTIATION"
    INHERITANCE = "INHERITANCE"
    TYPE_ANNOTATION = "TYPE_ANNOTATION"
    METHOD_CALL = "METHOD_CALL"
    ATTRIBUTE_ACCESS = "ATTRIBUTE_ACCESS"
    DECORATOR = "DECORATOR"


class ReferenceData(BaseModel):
    type: ReferenceType
    file: Path
    line: int
    column: int
    text: str


class CodeData(BaseModel):
    type: str
    repo: str
    file_path: Path
    name: str
    source_code: str
    docstring: str = ""
    parent_name: str = ""
    references: list[ReferenceData] = []

    @computed_field
    @property
    def module(self) -> str:
        return str(self.file_path.with_suffix("")).replace("/", ".").replace(self.repo, "")
