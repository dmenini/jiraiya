import logging
from pathlib import Path

from tqdm import tqdm

from doc_scribe.domain.data import ClassData, MethodData
from doc_scribe.code.vectore_store import CodeVectorStore

log = logging.getLogger(__name__)


class CodeBaseIndexer:
    def __init__(
        self,
        codebase_path: Path,
        class_data: list[ClassData],
        method_data: list[MethodData],
        vectorstore: CodeVectorStore,
    ) -> None:
        self.codebase_path = codebase_path.resolve()
        self.codebase_folder_name = self.codebase_path.name

        self.class_data = class_data
        self.method_data = method_data

        self.vectorstore = vectorstore

    def get_special_files(self) -> list[Path]:
        return list(self.codebase_path.rglob("*.md")) + list(self.codebase_path.rglob("*.sh"))

    def index(self) -> None:
        # Embed and add to class collection
        all_data = self.class_data + self.method_data
        for data in tqdm(all_data, total=len(all_data)):
            self.vectorstore.add(data=data)

        # Add markdown and shell files as class-like documents
        special_files = self.get_special_files()
        md_template = "File: {file_path}\n\nContent:\n{content}"

        if special_files:
            for file in tqdm(special_files, total=len(special_files)):
                content = file.read_text(encoding="utf-8")
                text = md_template.format(file_path=file, content=content)
                data = ClassData(repo=self.codebase_path.name, file_path=file, name=file.name, source_code=text)
                self.vectorstore.add(data=data)

        log.info("Added %d documents to vector store", len(all_data) + len(special_files))
