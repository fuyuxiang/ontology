"""ontology_name → ontology_id 解析层

Prompt 中 Agent 传入 ontology_name（本体英文标识，如 "RevenueRootCause"），
对应当前项目 ScenarioDict.code 字段。本模块提供统一转换。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.scenario import ScenarioDict


def resolve_ontology_id(db: Session, ontology_name: str) -> str | None:
    """将 ontology_name (ScenarioDict.code) 转换为 ontology_id (ScenarioDict.id)"""
    row = db.query(ScenarioDict).filter(ScenarioDict.code == ontology_name).first()
    if row:
        return row.id
    # 兼容：直接传入 id 的情况
    row = db.query(ScenarioDict).filter(ScenarioDict.id == ontology_name).first()
    if row:
        return row.id
    return None
