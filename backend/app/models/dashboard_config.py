from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DashboardConfig(Base):
    __tablename__ = "dashboard_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    cards_config: Mapped[list | None] = mapped_column(JSON)
    refresh_interval: Mapped[int] = mapped_column(Integer, default=30)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
