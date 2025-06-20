import json
import logging
from pathlib import Path

import yaml
from tqdm import tqdm

from doc_scribe.domain.config import Config
from doc_scribe.domain.data import CodeData
from doc_scribe.settings import Settings
from doc_scribe.store.vectore_store import VectorStore

log = logging.getLogger(__name__)

if __name__ == "__main__":
    settings = Settings()
    config_path = Path(__file__).parent / "agent_config.yaml"
    with config_path.open() as fp:
        config = yaml.safe_load(fp)
        config = Config.model_validate(config)

    dataset_path = Path("data/sam-20250226120731.json")

    vectorstore = VectorStore(
        tenant="test",
        dense_encoder=config.data.dense_encoder,
        bm25_encoder=config.data.bm25_encoder,
        late_encoder=config.data.late_encoder,
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )

    # vectorstore.clear()
    with dataset_path.open() as fp:
        documents = json.load(fp)

    #
    # documents = [doc for doc in documents if len(doc["content"]) >= 11000][55:]
    # documents = [doc for doc in documents if len(doc["content"]) < 15000]

    documents = [
        doc
        for doc in documents
        if doc["source"] == "https://www.swisscom.ch/de/privatkunden/hilfe/blue-tv/mehrere-geraete.html"
    ]

    parsed_data = [
        CodeData(
            repo=dataset_path.name,
            file_path=doc["source"],
            name=doc["title"],
            source_code=doc["content"],
        )
        for doc in documents
    ]

    for data in tqdm(parsed_data, total=len(parsed_data)):
        vectorstore.add(data=data)
