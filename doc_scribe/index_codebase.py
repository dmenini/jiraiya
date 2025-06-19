import logging
from pathlib import Path

import yaml

from doc_scribe.domain.enums import EncoderName
from doc_scribe.io.code_parser import CodeParser
from doc_scribe.settings import Settings
from doc_scribe.store.code_indexer import CodebaseIndexer
from doc_scribe.store.vectore_store import VectorStore

log = logging.getLogger(__name__)

if __name__ == "__main__":
    settings = Settings()
    config_path = Path(__file__).parent / "agent_config.yaml"
    with config_path.open() as fp:
        config = yaml.safe_load(fp)

    for codebase_path in config.data.codebases:
        log.info("Starting with codebase %s", codebase_path)

        code_parser = CodeParser(codebase_path=Path(codebase_path), blacklist=config.data.blacklist)

        for file, _ in code_parser.source_files:
            log.info(file)

        class_data, method_data = code_parser.extract_ast_nodes()
        class_data, method_data = code_parser.resolve_references(class_data, method_data)

        encoder = EncoderName.TITAN_V1
        vectorstore = VectorStore(
            tenant=config.data.tenant,
            dense_encoder=EncoderName[config.data.dense_encoder],
            bm25_encoder=config.data.bm25_encoder,
            late_encoder=config.data.late_encoder,
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )

        processor = CodebaseIndexer(
            codebase_path=Path(codebase_path),
            class_data=class_data,
            method_data=method_data,
            repository=vectorstore,
        )
        processor.index()
