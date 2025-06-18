from pathlib import Path

from doc_scribe.codebase.code_embedder import CodebaseIndexer
from doc_scribe.codebase.code_parser import CodeParser
from doc_scribe.codebase.code_store import CodebaseStore
from doc_scribe.domain.enums import EncoderName
from doc_scribe.encoder.cohere import CohereEmbeddings
from doc_scribe.encoder.titan import TitanEmbeddings

TENANT = "aaas"

codebase_path = Path("/Users/taamedag/Desktop/cai/aaas/upload-job/")
blacklist = ["tests", "integration_tests", "cicd"]

model = EncoderName.TITAN_V1

encoder_map = {
    EncoderName.COHERE_V3: CohereEmbeddings,
    EncoderName.TITAN_V1: TitanEmbeddings,
}

if __name__ == "__main__":
    code_parser = CodeParser(codebase_path=codebase_path, blacklist=blacklist)
    class_data, method_data = code_parser.extract_ast_nodes()
    class_data, method_data = code_parser.resolve_references(class_data, method_data)

    encoder = encoder_map[model](model=model, normalize=True)

    repository = CodebaseStore(tenant=TENANT, encoder=encoder, host="localhost", port=6333)
    processor = CodebaseIndexer(
        codebase_path=codebase_path,
        class_data=class_data,
        method_data=method_data,
        repository=repository,
    )
    processor.index()
