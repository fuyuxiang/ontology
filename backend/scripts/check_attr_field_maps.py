"""对比 EntityAttribute.source_field 与 Asset.schema_snapshot 物理列的差异。

仅做只读检查，不修改任何数据库记录。供 DDL 变更后核查本体属性映射是否需要人工更新。

设计目标：
- 列出当前 EntityAttribute 已映射但物理表已删除/改名的列（missing_in_snapshot）
- 列出物理表新增但 EntityAttribute 未跟进的列（missing_in_attrs）
- 列出两端同名但类型不一致的列（type_mismatch）
- 仅对带 schema_snapshot 的 Asset 才有意义；无 snapshot 的明确标注

执行（工作目录 backend/）：
    python -m scripts.check_attr_field_maps --entity InstallChurn   # 单个对象
    python -m scripts.check_attr_field_maps --all                   # 扫所有有 snapshot 的对象
    python -m scripts.check_attr_field_maps --all --json           # 结构化输出
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.asset import Asset
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.object_binding import ObjectBinding

logger = logging.getLogger(__name__)


def _binding_to_asset_table(db: Session, entity_id: str) -> tuple[str | None, str | None, Any]:
    """返回 (binding_id, asset_id, schema_snapshot) 或 (None, None, None)。"""
    binding = db.query(ObjectBinding).filter(
        ObjectBinding.object_type_id == entity_id,
        ObjectBinding.role == "primary",
    ).first()
    if not binding:
        return None, None, None
    asset = db.get(Asset, binding.asset_id)
    if not asset:
        return binding.id, None, None
    return binding.id, asset.id, asset.schema_snapshot


def _check_one(db: Session, entity: OntologyEntity) -> dict[str, Any]:
    """对一个对象做一次完整对比。"""
    binding_id, asset_id, snapshot = _binding_to_asset_table(db, entity.id)
    attrs = db.query(EntityAttribute).filter(EntityAttribute.entity_id == entity.id).all()

    result = {
        "entity": entity.name,
        "entity_id": entity.id,
        "binding_id": binding_id,
        "asset_id": asset_id,
        "has_snapshot": bool(snapshot),
        "missing_in_attrs": [],
        "missing_in_snapshot": [],
        "type_mismatch": [],
    }

    if not snapshot:
        return result

    snapshot_cols = {c["name"]: c for c in snapshot if isinstance(c, dict) and "name" in c}
    attr_fields = {(a.source_table or "", a.source_field or ""): a for a in attrs}

    # 1) snapshot 里有，attrs 没映射：缺映射
    asset_table = None
    if asset_id:
        asset_obj = db.get(Asset, asset_id)
        if asset_obj and asset_obj.locator:
            asset_table = asset_obj.locator.get("table")
    for col_name, col in snapshot_cols.items():
        matched = any(
            sf == col_name and (not asset_table or st == asset_table)
            for (st, sf), _ in attr_fields.items()
        )
        if not matched:
            result["missing_in_attrs"].append({
                "field": col_name,
                "type": col.get("type"),
                "comment": col.get("comment", ""),
            })

    # 2) attrs 映射了，snapshot 里没有：物理列可能已删/改名
    for (st, sf), attr in attr_fields.items():
        if not sf:
            continue
        if sf not in snapshot_cols:
            result["missing_in_snapshot"].append({
                "field": sf,
                "attr_name": attr.name,
                "type": attr.type,
            })
            continue
        # 3) 同名但类型不一致
        col = snapshot_cols[sf]
        col_type = (col.get("type") or "").lower()
        attr_type = (attr.type or "").lower()
        # 简化映射：attr_type 跟物理类型大致对应即可，差异>阈值视为 mismatch
        if col_type and attr_type and not _type_compatible(col_type, attr_type):
            result["type_mismatch"].append({
                "field": sf,
                "attr_name": attr.name,
                "attr_type": attr_type,
                "physical_type": col_type,
            })

    return result


# 类型兼容性：宽松匹配，不强制严格一致
_TYPE_ALIASES = {
    "string": {"varchar", "char", "text", "string", "nvarchar"},
    "number": {"int", "bigint", "decimal", "numeric", "float", "double", "number"},
    "date": {"date"},
    "datetime": {"datetime", "timestamp"},
    "ref": {"varchar", "char", "string"},  # 外键
}


def _type_compatible(physical: str, attr: str) -> bool:
    for group, aliases in _TYPE_ALIASES.items():
        if attr in group or attr in aliases:
            return physical in aliases or physical == group
    return physical == attr


def _print_text(results: list[dict[str, Any]]) -> None:
    if not results:
        print("无对象可对比（数据库中没有任何 published 的本体对象）。")
        return

    total_missing_in_attrs = sum(len(r["missing_in_attrs"]) for r in results)
    total_missing_in_snapshot = sum(len(r["missing_in_snapshot"]) for r in results)
    total_type_mismatch = sum(len(r["type_mismatch"]) for r in results)
    no_snapshot = sum(1 for r in results if not r["has_snapshot"])

    print(f"\n=== 对比摘要 ===")
    print(f"对象数: {len(results)}")
    print(f"无 schema_snapshot 跳过: {no_snapshot}")
    print(f"缺映射 (snapshot 有 / attrs 无): {total_missing_in_attrs}")
    print(f"列失效 (attrs 有 / snapshot 无): {total_missing_in_snapshot}")
    print(f"类型不一致: {total_type_mismatch}")

    for r in results:
        if not r["has_snapshot"]:
            print(f"\n[{r['entity']}] ⚠ 无 schema_snapshot，跳过")
            continue
        issues = len(r["missing_in_attrs"]) + len(r["missing_in_snapshot"]) + len(r["type_mismatch"])
        if issues == 0:
            print(f"\n[{r['entity']}] ✓ 一致（{len(r['missing_in_attrs']) + len(r['missing_in_snapshot']) + len(r['type_mismatch'])} 个差异）")
            continue
        print(f"\n[{r['entity']}] {issues} 个差异：")
        for m in r["missing_in_attrs"]:
            print(f"  · 缺映射: 物理列 {m['field']!r} ({m['type']}) 未对应到任何 EntityAttribute")
        for m in r["missing_in_snapshot"]:
            print(f"  · 列失效: 属性 {m['attr_name']!r} 映射到 {m['field']!r}，但物理表无此列")
        for m in r["type_mismatch"]:
            print(f"  · 类型不一致: {m['field']!r} attr={m['attr_type']} 物理={m['physical_type']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="对比 EntityAttribute 与 Asset.schema_snapshot")
    parser.add_argument("--entity", help="单个本体对象 name（如 InstallChurn）")
    parser.add_argument("--all", action="store_true", help="扫所有有 binding 的对象")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = parser.parse_args()

    if not args.entity and not args.all:
        parser.error("必须指定 --entity <name> 或 --all")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    db = SessionLocal()
    try:
        if args.entity:
            entities = db.query(OntologyEntity).filter(OntologyEntity.name == args.entity).all()
            if not entities:
                print(f"对象 {args.entity!r} 不存在。", file=sys.stderr)
                return 2
        else:
            # 找所有有 primary binding 的对象
            bound_ids = [r[0] for r in db.query(ObjectBinding.object_type_id)
                         .filter(ObjectBinding.role == "primary").distinct().all()]
            entities = db.query(OntologyEntity).filter(OntologyEntity.id.in_(bound_ids)).all()
            if not entities:
                print("无任何已绑定对象。", file=sys.stderr)
                return 2

        results = [_check_one(db, e) for e in entities]
    finally:
        db.close()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_text(results)

    # 任何差异或缺 snapshot 都返回 1，让 CI 能 fail
    has_issues = any(
        r["missing_in_attrs"] or r["missing_in_snapshot"] or r["type_mismatch"] or not r["has_snapshot"]
        for r in results
    )
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
