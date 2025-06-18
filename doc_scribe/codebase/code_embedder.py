import logging
from pathlib import Path

from doc_scribe.codebase.code_store import CodebaseStore
from doc_scribe.domain.code_data import ClassData, MethodData

log = logging.getLogger(__name__)


class CodebaseIndexer:
    def __init__(
        self,
        codebase_path: Path,
        class_data: list[ClassData],
        method_data: list[MethodData],
        repository: CodebaseStore,
    ) -> None:
        self.codebase_path = codebase_path.resolve()
        self.codebase_folder_name = self.codebase_path.name

        self.class_data = class_data
        self.method_data = method_data

        # Initialize ChromaDB
        self.repository = repository

    def get_special_files(self) -> list[Path]:
        return list(self.codebase_path.rglob("*.md")) + list(self.codebase_path.rglob("*.sh"))

    def index(self) -> None:
        # Embed and add to class collection
        all_data = self.class_data + self.method_data
        for data in all_data:
            self.repository.add(data=data)

        # Add markdown and shell files as class-like documents
        special_files = self.get_special_files()
        md_template = "File: {file_path}\n\nContent:\n{content}"

        if special_files:
            for file in special_files:
                content = file.read_text(encoding="utf-8")
                text = md_template.format(file_path=file, content=content)
                data = ClassData(repo=self.codebase_path.name, file_path=file, name=file.name, source_code=text)
                self.repository.add(data=data)

        log.info("Added %d documents to vector store", len(all_data) + len(special_files))
