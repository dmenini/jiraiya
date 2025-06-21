import logging
from pathlib import Path

import yaml
from tqdm import tqdm

from doc_scribe.agent.components import create_docs_writer
from doc_scribe.domain.config import Config
from doc_scribe.domain.data import TextData
from doc_scribe.domain.documentation import TechnicalDoc
from doc_scribe.io.code_parser import CodeBaseParser
from doc_scribe.settings import Settings
from doc_scribe.store.code_store import CodeVectorStore

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

log = logging.getLogger(__name__)

if __name__ == "__main__":
    settings = Settings()
    config_path = Path(__file__).parent / "agent_config.yaml"
    with config_path.open() as fp:
        config = yaml.safe_load(fp)
        config = Config.model_validate(config)

    writer = create_docs_writer(config.agent)

    for codebase_path in config.data.codebases:
        path = Path(codebase_path)
        log.info("Starting with codebase %s", codebase_path)

        code_parser = CodeBaseParser(codebase_path=path, blacklist=config.data.blacklist)

        for file, _ in code_parser.source_files:
            log.info(file)

        data = code_parser.extract_ast_nodes()
        data = code_parser.resolve_references(data)

        vectorstore = CodeVectorStore(
            tenant=config.data.tenant,
            code_encoder=config.data.code_encoder,
            text_encoder=config.data.dense_encoder,
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        vectorstore.clear()

        for dp in tqdm(data, total=len(data)):
            response = writer.run_sync(user_prompt=dp.source_code)
            output: TechnicalDoc = response.output

            text = TextData(
                repo=dp.repo,
                name=dp.name,
                file_path=dp.file_path,
                text=output.to_markdown(path=str(dp.file_path)),
            )

            vectorstore.add_code(data=dp)
            vectorstore.add_text(data=text)

        # Add markdown documents
        special_files = list(path.rglob("*.md")) + list(path.rglob("*.sh"))
        md_template = "File: {file_path}\n\nContent:\n{content}"

        if special_files:
            for file in tqdm(special_files, total=len(special_files)):
                content = file.read_text(encoding="utf-8")
                text = TextData(
                    repo=path.name,
                    name=file.name,
                    file_path=file,
                    text=md_template.format(file_path=file, content=content),
                )
                vectorstore.add_text(data=text)

        log.info("Added %d documents to vector store", len(data) + len(special_files))
