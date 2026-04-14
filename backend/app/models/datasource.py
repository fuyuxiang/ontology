import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class DataSource(Base):
    __tablename__ = "datasources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # mysql, postgresql, oracle, sqlserver, clickhouse, hive, kafka, elasticsearch, api
    host: Mapped[str] = mapped_column(String(200), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database: Mapped[str] = mapped_column(String(100), default="")
    username: Mapped[str] = mapped_column(String(100), default="")
    password: Mapped[str] = mapped_column(String(200), default="")
    params: Mapped[dict | None] = mapped_column(JSON)  # extra connection params
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, inactive, error
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))
