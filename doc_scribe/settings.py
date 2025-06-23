from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    max_file_count: int = 100
    """Limit of files for generating the file level code analysis.
    If the project contains more files than this, we will simply use the module level analysis
    as documentation source for the high level documentation.
    """

    aws_default_region: str = "eu-central-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: SecretStr = ""
    aws_session_token: SecretStr = ""

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    jira_server: str = ""
    jira_token: SecretStr = ""
