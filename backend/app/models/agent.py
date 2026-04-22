import uuid
from datetime import datetime
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai/ollama/dashscope/azure/custom
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_base: Mapped[str | None] = mapped_column(Text)
    api_key: Mapped[str | None] = mapped_column(Text)
    capabilities: Mapped[list | None] = mapped_column(JSON)  # ["chat","vision","asr","embedding"]
    config_json: Mapped[dict | None] = mapped_column(JSON)   # temperature, max_tokens, etc.
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list | None] = mapped_column(JSON)
    model_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("model_registry.id", ondelete="SET NULL"))
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    kb_ids: Mapped[list | None] = mapped_column(JSON)      # knowledge base ids
    entity_ids: Mapped[list | None] = mapped_column(JSON)  # ontology entity ids
    tools_config: Mapped[dict | None] = mapped_column(JSON)
    nodes_json: Mapped[list | None] = mapped_column(JSON)   # workflow canvas nodes
    edges_json: Mapped[list | None] = mapped_column(JSON)   # workflow canvas edges
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/published
    api_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
