from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.agent import gen_uuid


class EvalSuite(Base):
    __tablename__ = "eval_suites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    suite_id: Mapped[str] = mapped_column(String(36), ForeignKey("eval_suites.id", ondelete="CASCADE"))
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_keywords: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    suite_id: Mapped[str] = mapped_column(String(36), ForeignKey("eval_suites.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="running")
    metrics: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("eval_runs.id", ondelete="CASCADE"))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("eval_cases.id", ondelete="CASCADE"))
    actual_output: Mapped[str] = mapped_column(Text, default="")
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
