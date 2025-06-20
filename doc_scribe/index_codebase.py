import logging
from pathlib import Path

import yaml

from doc_scribe.domain.config import Config
from doc_scribe.io.code_parser import CodeBaseParser
from doc_scribe.settings import Settings

log = logging.getLogger(__name__)

if __name__ == "__main__":
    settings = Settings()
    config_path = Path(__file__).parent / "agent_config.yaml"
    with config_path.open() as fp:
        config = yaml.safe_load(fp)
        config = Config.model_validate(config)

    for codebase_path in config.data.codebases:
        path = Path(codebase_path)
        log.info("Starting with codebase %s", codebase_path)

        code_parser = CodeBaseParser(codebase_path=path, blacklist=config.data.blacklist)

        for file, _ in code_parser.source_files:
            log.info(file)

        data = code_parser.extract_ast_nodes()
        data = code_parser.resolve_references(data)

        # vectorstore = VectorStore(
        #     tenant=config.data.tenant,
        #     dense_encoder=config.data.dense_encoder,
        #     bm25_encoder=config.data.bm25_encoder,
        #     late_encoder=config.data.late_encoder,
        #     host=settings.qdrant_host,
        #     port=settings.qdrant_port,
        # )

        # Embed and add to class collection
        # for dp in tqdm(data, total=len(data)):
        #     vectorstore.add(data=dp)
        #
        # # Add markdown and shell files as class-like documents
        # special_files = list(path.rglob("*.md")) + list(path.rglob("*.sh"))
        # md_template = "File: {file_path}\n\nContent:\n{content}"
        #
        # if special_files:
        #     for file in tqdm(special_files, total=len(special_files)):
        #         content = file.read_text(encoding="utf-8")
        #         text = md_template.format(file_path=file, content=content)
        #         data = CodeData(
        #             type="extra",
        #             repo=path.name,
        #             module=file.name,
        #             file_path=file,
        #             name=file.name,
        #             source_code=text,
        #         )
        #         vectorstore.add(data=data)
        #
        # log.info("Added %d documents to vector store", len(data) + len(special_files))
