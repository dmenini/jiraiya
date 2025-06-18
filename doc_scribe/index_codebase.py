import logging
from pathlib import Path

from doc_scribe.codebase.code_embedder import CodebaseIndexer
from doc_scribe.codebase.code_parser import CodeParser
from doc_scribe.codebase.code_store import CodebaseStore
from doc_scribe.domain.enums import EncoderName

log = logging.getLogger(__name__)

TENANT = "aaas"

codebase_path = Path("/Users/taamedag/Desktop/cai/aaas/upload-job/")
blacklist = ["tests", "integration_tests", "cicd"]

if __name__ == "__main__":
    code_parser = CodeParser(codebase_path=codebase_path, blacklist=blacklist)

    for file, lang in code_parser.source_files:
        log.info(file)

    class_data, method_data = code_parser.extract_ast_nodes()
    class_data, method_data = code_parser.resolve_references(class_data, method_data)

    encoder = EncoderName.TITAN_V1
    vectorstore = CodebaseStore(tenant=TENANT, encoder=encoder, host="localhost", port=6333)

    processor = CodebaseIndexer(
        codebase_path=codebase_path,
        class_data=class_data,
        method_data=method_data,
        repository=vectorstore,
    )
    processor.index()
