from pathlib import Path

from doc_scribe.codebase.code_parser import CodeParser
from doc_scribe.codebase.code_store import CodebaseStore
from doc_scribe.domain.code_data import ClassData, MethodData
from doc_scribe.domain.enums import EncoderName
from doc_scribe.encoder.base import Embeddings
from doc_scribe.encoder.cohere import CohereEmbeddings
from doc_scribe.encoder.titan import TitanEmbeddings


class CodebaseEmbedder:
    def __init__(
        self,
        codebase_path: Path,
        class_data: list[ClassData],
        method_data: list[MethodData],
        encoder: Embeddings,
        repository: CodebaseStore,
    ):
        self.codebase_path = codebase_path.resolve()
        self.codebase_folder_name = self.codebase_path.name

        self.class_data = class_data
        self.method_data = method_data

        self.embedding_model = encoder

        # Initialize ChromaDB
        self.repository = repository

    def get_special_files(self):
        return list(self.codebase_path.rglob("*.md")) + list(self.codebase_path.rglob("*.sh"))

    def index(self):
        # Embed and add to class collection
        class_template = "File: {file_path}\n\nClass: {class_name}\n\nSource Code:\n{source_code}\n\n"
        for data in self.class_data:
            text = class_template.format(
                file_path=data.file_path, class_name=data.name, source_code=data.source_code
            )
            vector = self.embedding_model.embed_documents([text])[0]
            self.repository.add(data=data, text=text, vector=vector)

        # Embed and add to method collection
        for data in self.method_data:
            text = data.source_code
            vector = self.embedding_model.embed_documents([text])[0]
            self.repository.add(data=data, text=text, vector=vector)

        # Add markdown and shell files as class-like documents
        special_files = self.get_special_files()
        md_template = "File: {file_path}\n\nContent:\n{content}"

        if special_files:
            for file in special_files:
                content = file.read_text(encoding="utf-8")
                text = md_template.format(file_path=file, content=content)
                vector = self.embedding_model.embed_documents([text])[0]
                data = ClassData(
                    file_path=file,
                    name=file.name,
                    source_code=text
                )
                self.repository.add(data=data, text=text, vector=vector)

        print("ChromaDB: embedded method and class data successfully.")


if __name__ == "__main__":
    codebase_path = Path("/Users/taamedag/Desktop/cai/aaas/upload-job/")
    blacklist = ["tests", "integration_tests", "cicd"]
    code_parser = CodeParser(codebase_path=codebase_path, blacklist=blacklist)
    class_data, method_data = code_parser.extract_ast_nodes()
    class_data, method_data = code_parser.resolve_references(class_data, method_data)

    model = EncoderName.TITAN_V1

    encoder_map = {
        EncoderName.COHERE_V3: CohereEmbeddings,
        EncoderName.TITAN_V1: TitanEmbeddings,
    }

    encoder = encoder_map[model](model=model, normalize=True)

    repository = CodebaseStore(tenant="aaas")
    processor = CodebaseEmbedder(codebase_path=codebase_path, class_data=class_data, method_data=method_data,
                                 encoder=encoder, repository=repository)
    processor.index()
