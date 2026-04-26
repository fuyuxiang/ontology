from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./ontology.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "ontology123"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LLM_API_BASE: str = "https://coding.dashscope.aliyuncs.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen3.5-plus"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
