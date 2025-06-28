import logging
from pathlib import Path

import yaml
from tqdm import tqdm

from jiraiya.agent.components import create_docs_writer
from jiraiya.domain.config import Config
from jiraiya.domain.data import TextData
from jiraiya.domain.documentation import TechnicalDoc
from jiraiya.indexing.code_parser import CodeBaseParser
from jiraiya.settings import Settings
from jiraiya.store.code_store import CodeVectorStore

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

log = logging.getLogger(__name__)

if __name__ == "__main__":
    settings = Settings()
    config_path = Path(__file__).parent / "config.yaml"
    with config_path.open() as fp:
        config = yaml.safe_load(fp)
        config = Config.model_validate(config)

    vectorstore = CodeVectorStore(
        tenant=config.data.tenant,
        code_encoder=config.data.code_encoder,
        text_encoder=config.data.dense_encoder,
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )

    if config.data.reset:
        vectorstore.clear()

    writer = create_docs_writer(config.agent)

    for codebase_path in config.data.codebases:
        path = Path(codebase_path)
        log.info("Starting with codebase %s", codebase_path)

        code_parser = CodeBaseParser(codebase_path=path, blacklist=config.data.blacklist)

        for file, _ in code_parser.source_files:
            log.info(file)

        # Extract classes and top level functions from the codebase
        data = code_parser.extract_ast_nodes()
        data = code_parser.resolve_references(data)

        # Generate documentation for each code object
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

        # Add markdown documents and shell scripts
        special_files = list(path.rglob("*.md")) + list(path.rglob("*.sh"))
        md_template = "File: {file_path}\n\nContent:\n{content}"

        if special_files:
            log.info(special_files)
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
