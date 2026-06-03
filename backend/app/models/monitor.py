from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from app.database import Base


class ServiceMetric(Base):
    __tablename__ = "t_service_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="healthy")  # healthy / warning / unhealthy
    response_ms = Column(Float, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_service_metric_collected_at", "collected_at"),
        Index("ix_service_metric_service_name", "service_name"),
    )


class LLMCallRecord(Base):
    __tablename__ = "t_llm_call_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caller_module = Column(String(50), nullable=False)  # copilot / agent / builder / rule_engine
    model_name = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_llm_call_created_at", "created_at"),
        Index("ix_llm_call_caller_module", "caller_module"),
    )


class Alert(Base):
    __tablename__ = "t_alert"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # critical / warning / info
    service_name = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_alert_created_at", "created_at"),
        Index("ix_alert_resolved", "resolved"),
    )
