from pathlib import Path

from pydantic import BaseModel


class ReferenceData(BaseModel):
    file: Path
    line: int
    column: int
    text: str


class CodeData(BaseModel):
    file_path: Path
    name: str
    source_code: str
    docstring: str = ""
    parent_name: str = ""
    references: list[ReferenceData] = []


class ClassData(CodeData):
    constructor_declaration: str = ""
    method_declarations: str = ""


class MethodData(CodeData):
    pass
