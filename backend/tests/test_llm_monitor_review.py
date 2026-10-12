"""Actual resolver completion paths must persist accurate monitoring outcomes."""
from types import SimpleNamespace as N

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.monitor import LLMCallRecord
from app.repositories.monitor_repo import MonitorRepository
from app.services.llm_resolver import _instrument_client


def chunk(reason=None, usage=None):
    return N(choices=[N(finish_reason=reason)], usage=usage)


def test_completion_stream_failure_and_cancel_are_persisted_without_caller_commit(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'metrics.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    replies = [N(choices=[N(finish_reason="stop")], usage=N(prompt_tokens=3, completion_tokens=2)),
               iter([chunk(), chunk("stop", N(prompt_tokens=4, completion_tokens=5))]),
               iter([chunk()]), iter([chunk(), chunk("stop")])]
    def provider(**kwargs):
        if kwargs.get("model") == "broken":
            raise RuntimeError("provider rejected")
        return replies.pop(0)
    client = _instrument_client(N(chat=N(completions=N(create=provider))), db, "ontology")
    client.chat.completions.create(model="working", messages=[{"content": "private prompt"}])
    assert len(list(client.chat.completions.create(model="working", stream=True))) == 2
    with pytest.raises(ValueError, match="未完整结束"):
        list(client.chat.completions.create(model="truncated", stream=True))
    stream = client.chat.completions.create(model="cancelled", stream=True)
    next(stream)
    stream.close()
    with pytest.raises(RuntimeError, match="provider rejected"):
        client.chat.completions.create(model="broken")
    with sessionmaker(bind=engine)() as read:
        records = read.query(LLMCallRecord).order_by(LLMCallRecord.id).all()
        assert [r.success for r in records] == [True, True, False, False, False]
        assert records[0].prompt_tokens == 3 and records[1].completion_tokens == 5
        assert all(r.latency_ms >= 0 for r in records)
        stats = MonitorRepository(read).get_llm_stats_24h()
        assert stats["total_24h"] == 5 and stats["failed_count"] == 3 and stats["success_rate"] == 40
        assert stats["by_module"]["ontology"]["success_count"] == 2
    db.close()
    engine.dispose()


def test_metrics_do_not_commit_conversation_and_survive_its_rollback(tmp_path):
    from app.models.user import User
    engine = create_engine(f"sqlite:///{tmp_path / 'transaction.db'}", connect_args={"timeout": 0.1})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(User(id="must-rollback", username="pending", password_hash="unused", name="Pending", role="viewer"))
        db.flush()
        client = _instrument_client(N(chat=N(completions=N(create=lambda **_: N(choices=[N(finish_reason="stop")], usage=None)))), db, "general")
        client.chat.completions.create(model="real-call")
        with factory() as read:
            assert read.query(LLMCallRecord).count() == 0
            assert read.get(User, "must-rollback") is None
        db.rollback()
        with factory() as read:
            assert read.get(User, "must-rollback") is None
            assert read.query(LLMCallRecord).one().success is True
    engine.dispose()
