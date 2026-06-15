import sys
from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./ontology.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LLM_BASE_URL: str = "https://coding.dashscope.aliyuncs.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen3.5-plus"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = False

    DWD_DATABASE_URL: str = ""
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "milvus"

    CORS_ORIGINS: str = "http://localhost:5173"
    ADMIN_INITIAL_PASSWORD: str = ""
    CREDENTIAL_ENCRYPTION_KEY: str = ""

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()

_REQUIRED_SECRETS = ["SECRET_KEY"]
_missing = [k for k in _REQUIRED_SECRETS if not getattr(settings, k)]
if _missing:
    print(f"[FATAL] 缺少必要的环境变量: {', '.join(_missing)}。请配置 .env 文件。", file=sys.stderr)
    sys.exit(1)
