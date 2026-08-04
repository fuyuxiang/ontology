"""阶段 0：为 broadband 业务的 14 个 bb_* 资产建立 ObjectBinding(role=primary)。

本脚本对应 docs/broadband-ontology-migration.md 阶段 0 的落地实现：
- 把 14 个退单稽核本体对象（按 name 匹配）分别绑定到对应的 bb.* Asset
- 由 ObjectBindingService.create 自动处理反向引用与 EntityAttribute.source_field 镜像
- 已存在的 binding 跳过，不重复创建

设计原则：
- **不自动创建**本体对象或 Asset——前者是用户数据，后者由 seed_business_assets 负责
- 任一前提缺失（对象未建或资产未注册）则报错并打印补救路径，由用户决定
- 提供 --dry-run 仅打印计划，--json 输出结构化报告

执行（工作目录必须是 backend/）：
    cd backend
    python -m scripts.seed_broadband_bindings           # 实际建立
    python -m scripts.seed_broadband_bindings --dry-run # 仅预览
    python -m scripts.seed_broadband_bindings --json    # 结构化输出
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.entity import OntologyEntity
from app.repositories.asset_repo import AssetRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.object_binding_service import ObjectBindingService

logger = logging.getLogger(__name__)


# (object_name, asset_alias)
# asset_alias 与 seed_business_assets._bb_tables() 中注册的一致
_BB_BINDINGS: list[tuple[str, str]] = [
    ("InstallChurn",    "bb.churn"),
    ("InstallOrder",    "bb.order"),
    ("Customer",        "bb.customer"),
    ("Engineer",        "bb.engineer"),
    ("DispatchRecord",  "bb.dispatch"),
    ("Address",         "bb.address"),
    ("Channel",         "bb.channel"),
    ("Product",         "bb.product"),
    ("EngineerCall",    "bb.engineer_call"),
    ("CallbackCall",    "bb.callback_call"),
    ("CompetitorCall",  "bb.competitor_call"),
    ("PendingPool",     "bb.pending_pool"),
    ("Evidence",        "bb.evidence"),
    ("AuditTrail",      "bb.audit_trail"),
]


def _resolve(db: Session, dry_run: bool) -> tuple[list[dict[str, Any]], list[str]]:
    """解析所有 entity 与 asset；返回计划列表与错误列表。"""
    entity_repo_by_name = {e.name: e for e in
                           db.query(OntologyEntity).filter(OntologyEntity.name.in_(
                               [n for n, _ in _BB_BINDINGS]
                           )).all()}
    asset_repo = AssetRepository(db)
    asset_by_alias = {a.alias: a for a in
                      db.query(__import__('app.models.asset', fromlist=['Asset']).Asset).all()
                      if a.alias in [al for _, al in _BB_BINDINGS]}

    plans: list[dict[str, Any]] = []
    errors: list[str] = []

    for obj_name, alias in _BB_BINDINGS:
        entity = entity_repo_by_name.get(obj_name)
        asset = asset_by_alias.get(alias) or asset_repo.find_by_alias(alias)

        if entity is None:
            errors.append(
                f"本体对象「{obj_name}」不存在。"
                f"请在界面新建本体对象或通过 POST /api/v1/entities/from-file 导入，"
                f"对象 name 必须为「{obj_name}」。"
            )
            continue
        if asset is None:
            errors.append(
                f"资产 alias「{alias}」不存在。"
                f"请先执行 python -m backend.scripts.seed_business_assets 完成 Asset 注册。"
            )
            continue

        # 已存在 binding？
        existing = ObjectBindingRepository(db).find_existing(entity.id, asset.id, "primary")
        plans.append({
            "object_name": obj_name,
            "entity_id": entity.id,
            "asset_alias": alias,
            "asset_id": asset.id,
            "table": (asset.locator or {}).get("table", ""),
            "action": "skip" if existing else "create",
        })

    return plans, errors


def _apply(db: Session, plans: list[dict[str, Any]]) -> dict[str, int]:
    svc = ObjectBindingService(db)
    stats = {"created": 0, "skipped": 0, "failed": 0}
    for p in plans:
        if p["action"] == "skip":
            stats["skipped"] += 1
            continue
        try:
            svc.create(object_type_id=p["entity_id"], asset_id=p["asset_id"], role="primary")
            stats["created"] += 1
            logger.info("创建 binding: %s → %s", p["object_name"], p["asset_alias"])
        except (ValueError, LookupError) as e:
            stats["failed"] += 1
            logger.error("创建 binding 失败 %s → %s: %s", p["object_name"], p["asset_alias"], e)
            db.rollback()
    db.commit()
    return stats


def _print_text(plans: list[dict[str, Any]], errors: list[str], dry_run: bool) -> None:
    if errors:
        print("前置条件不满足，无法继续：", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
    if not plans and not errors:
        print("无 binding 待处理。")
        return
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}绑定计划（共 {len(plans)} 项）：")
    print(f"  {'对象':<18} {'entity_id':<38} {'asset_alias':<18} {'物理表':<22} {'操作'}")
    for p in plans:
        print(f"  {p['object_name']:<18} {p['entity_id']:<38} {p['asset_alias']:<18} {p['table']:<22} {p['action']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="为 broadband 业务资产建立 ObjectBinding")
    parser.add_argument("--dry-run", action="store_true", help="仅打印计划，不写库")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON 报告")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出 DEBUG 日志")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    db = SessionLocal()
    try:
        plans, errors = _resolve(db, args.dry_run)
    finally:
        db.close()

    if args.json:
        print(json.dumps({"plans": plans, "errors": errors,
                          "summary": {"plan_count": len(plans), "error_count": len(errors)}},
                         ensure_ascii=False, indent=2))
        return 0 if not errors else 2

    _print_text(plans, errors, args.dry_run)

    if errors:
        return 2
    if args.dry_run:
        print("\n提示：去掉 --dry-run 实际执行。")
        return 0

    db = SessionLocal()
    try:
        stats = _apply(db, plans)
    finally:
        db.close()
    print(f"\n完成：创建 {stats['created']}，跳过 {stats['skipped']}，失败 {stats['failed']}")
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
