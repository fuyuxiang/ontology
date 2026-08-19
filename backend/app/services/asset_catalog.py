"""面向 AI 构建流程的通用结构化资产目录。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.repositories.asset_repo import AssetRepository


def _table_name(asset: Asset) -> str:
    locator = asset.locator or {}
    return str(locator.get("table") or asset.name)


def _find_asset(db: Session | None, table_name: str) -> Asset | None:
    if db is None:
        return None
    for asset in AssetRepository(db).list_active_structured():
        if table_name in {_table_name(asset), asset.name, asset.alias}:
            return asset
    return None


def get_tables(db: Session | None) -> list[dict]:
    """返回已注册且可用的结构化资产，不依赖任何特定目录表。"""
    if db is None:
        return []
    return [
        {
            "asset_id": asset.id,
            "table_name": _table_name(asset),
            "table_desc": asset.description or asset.alias or asset.name,
            "kind": asset.kind,
            "domain": asset.domain,
        }
        for asset in AssetRepository(db).list_active_structured()
    ]


def get_table_schema(table_name: str, db: Session | None) -> list[dict]:
    """将资产的 schema_snapshot 转为 AI 构建流程使用的统一字段格式。"""
    asset = _find_asset(db, table_name)
    if not asset:
        return []

    return [
        {
            "field_name": column.get("name", ""),
            "field_desc": column.get("comment") or column.get("description") or "",
            "field_type": column.get("type", ""),
        }
        for column in (asset.schema_snapshot or [])
        if column.get("name")
    ]
