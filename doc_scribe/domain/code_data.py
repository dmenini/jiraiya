from pathlib import Path

from pydantic import BaseModel


class ReferenceData(BaseModel):
    file: Path
    line: int
    column: int
    text: str


class CodeData(BaseModel):
    repo: str
    file_path: Path
    name: str
    source_code: str
    docstring: str = ""
    parent_name: str = ""
    references: list[ReferenceData] = []


class ClassData(CodeData):
    pass


class MethodData(CodeData):
    pass
