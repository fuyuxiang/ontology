"""
AIP 场景执行包装器
- 从 AipScene 加载 nodes/edges
- 创建 AipSceneExecution 行（status=running）
- 调 GraphEngine.run_for_scene() yield SSE 事件
- 完成时把 node_io / final_output / 状态落库
- 同步双输出：① 给前端的 SSE 事件流；② 给 DB 的执行记录
"""
from __future__ import annotations

import json
import time
import logging
from datetime import datetime
from typing import Any, Generator

from sqlalchemy.orm import Session

from app.config import settings
from app.models.scene import AipScene, AipSceneExecution, AipSceneTrigger
from app.models.agent import ModelRegistry
from app.services.agent.graph_engine import GraphEngine
from app.utils.identifiers import gen_uuid

logger = logging.getLogger(__name__)


def _resolve_model_config(db: Session) -> tuple[str | None, dict]:
    """返回 (model_name, model_config) — 没配置则返回 (None, {}) 让 GraphEngine 走 settings 默认。"""
    m = db.query(ModelRegistry).filter(ModelRegistry.status == "active").first()
    if not m:
        return None, {}
    cfg: dict = {}
    if m.api_key:
        cfg["api_key"] = m.api_key
    if m.api_base:
        cfg["api_base"] = m.api_base
    if m.config_json:
        cfg.update(m.config_json)
    return m.model_name, cfg


def create_execution_row(
    db: Session,
    scene: AipScene,
    triggered_by: str,
    trigger_payload: dict | None,
    input_params: dict | None,
) -> AipSceneExecution:
    exc = AipSceneExecution(
        id=gen_uuid(),
        scene_id=scene.id,
        scene_name=scene.name,
        scene_version=scene.version or 0,
        status="running",
        triggered_by=triggered_by,
        trigger_payload=trigger_payload or {},
        input_params=input_params or {},
        node_results={},
        final_output={},
        started_at=datetime.utcnow(),
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc


def run_scene_stream(
    db: Session,
    scene: AipScene,
    execution: AipSceneExecution,
    input_params: dict | None = None,
) -> Generator[dict, None, None]:
    """阻塞式生成器：跑场景 + 落库 + yield 事件。"""
    if not scene.nodes_json:
        yield {"type": "scene_failed", "error": "画布为空，请先添加节点", "execution_id": execution.id}
        execution.status = "failed"
        execution.error_message = "画布为空"
        execution.finished_at = datetime.utcnow()
        execution.duration_ms = 0
        db.commit()
        return

    model_name, model_config = _resolve_model_config(db)
    engine = GraphEngine(
        db,
        nodes_json=scene.nodes_json or [],
        edges_json=scene.edges_json or [],
        system_prompt=scene.description or "",
        model_name=model_name,
        model_config=model_config,
        emit_node_io=True,
    )

    yield {"type": "execution_started", "execution_id": execution.id, "scene_id": scene.id, "scene_name": scene.name}

    t0 = time.time()
    failed = False
    final_output: dict = {}
    last_error: str | None = None

    try:
        for ev in engine.run_for_scene(input_params or execution.input_params or {}):
            if ev.get("type") == "scene_finished":
                final_output = ev.get("final_output", {})
            elif ev.get("type") == "scene_failed":
                failed = True
                last_error = ev.get("error") or "未知错误"
            yield ev
    except Exception as e:
        logger.exception("[scene_runner] 异常")
        failed = True
        last_error = str(e)
        yield {"type": "scene_failed", "error": str(e), "execution_id": execution.id}

    duration_ms = int((time.time() - t0) * 1000)
    execution.status = "failed" if failed else "success"
    execution.node_results = engine.node_io
    execution.final_output = final_output
    execution.finished_at = datetime.utcnow()
    execution.duration_ms = duration_ms
    execution.error_message = last_error
    db.commit()

    yield {
        "type": "execution_finished",
        "execution_id": execution.id,
        "status": execution.status,
        "duration_ms": duration_ms,
        "final_output": final_output,
    }


def sse_format(event: dict) -> str:
    """SSE 事件序列化（标准 EventStream 格式）"""
    et = event.get("type", "message")
    payload = json.dumps(event, ensure_ascii=False, default=str)
    return f"event: {et}\ndata: {payload}\n\n"


def run_scene_in_thread(
    scene_id: str,
    triggered_by: str,
    trigger_payload: dict | None = None,
    input_params: dict | None = None,
) -> str:
    """后台线程入口（用于触发器 / replay）：开新 DB 会话，跑完场景，丢弃事件。
    返回 execution_id。
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        scene = db.get(AipScene, scene_id)
        if not scene:
            raise RuntimeError(f"场景 {scene_id} 不存在")
        execution = create_execution_row(db, scene, triggered_by, trigger_payload, input_params)
        for _ev in run_scene_stream(db, scene, execution, input_params):
            pass
        return execution.id
    finally:
        db.close()
