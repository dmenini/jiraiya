from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    aws_default_region: str = "eu-central-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: SecretStr = ""
    aws_session_token: SecretStr = ""

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    jira_server: str = ""
    jira_token: SecretStr = ""
