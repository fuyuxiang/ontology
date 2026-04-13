from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ontology"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ANTHROPIC_API_KEY: str = ""
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
