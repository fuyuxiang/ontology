"""业务侧 sql_view Asset 种子脚本。

作用：把 mnp / scenes / broadband 三个业务模块原本散落在 Python 文件里的硬编码 SQL，
全部抽为 kind=sql_view 的 Asset，并通过 alias 暴露给 ExecuteService.execute_alias。

执行时机：
- 应用 lifespan 启动时调用 seed()（幂等）
- 或独立运行：python -m backend.scripts.seed_business_assets

依赖：
- 目标 Connection 必须由用户在"数据接入·连接"页面预先创建（或通过 /api/v1/connections 创建）。
  本脚本仅按名称 (BB_CONN_NAME，默认 bb_audit_db) 查找，**不再写死 host/账号/密码**。
- 找不到 Connection 时，仅记录 warning 并跳过业务资产 seed，不阻断启动。
- base table Asset / sql_view Asset 在 Connection 已就绪时自动注册。
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.asset import Asset
from app.models.connection import Connection
from app.repositories.asset_repo import AssetRepository
from app.repositories.connection_repo import ConnectionRepository
from app.services.data_plane.asset_service import AssetService

logger = logging.getLogger(__name__)


# 业务连接名称（用户需在"数据接入·连接"页面提前创建该名称的 Connection）
_BB_CONN_NAME = os.getenv("BB_CONN_NAME", "bb_audit_db")


# ── 业务侧 Asset 配置 ────────────────────────────────────────────

# (alias, name, base_table_name, sql, description)
SqlViewSeed = tuple[str, str, str, str, str]


def _mnp_seeds() -> list[SqlViewSeed]:
    return [
        ("mnp.user_count", "MNP 总用户数", "dwa_v_d_cus_cb_user_info",
         "SELECT COUNT(*) AS n FROM <asset>", "MNP 用户主表行数"),
        ("mnp.query_user_count", "MNP 携转查询用户数", "dwd_d_cus_np_turn_query_user",
         "SELECT COUNT(DISTINCT device_number) AS n FROM <asset>", ""),
        ("mnp.maintain_total", "MNP 维挽记录数", "dwd_d_cus_qk_turn_maintain",
         "SELECT COUNT(*) AS n FROM <asset>", ""),
        ("mnp.maintain_success", "MNP 维挽成功数", "dwd_d_cus_qk_turn_maintain",
         "SELECT COUNT(*) AS n FROM <asset> WHERE is_success_maintain='1'", ""),
        ("mnp.complaint_total", "MNP 客服工单总数", "dwd_d_evt_kf_order_main",
         "SELECT COUNT(*) AS n FROM <asset>", ""),
        ("mnp.owe_users", "MNP 欠费用户数", "dwd_m_mrt_al_chl_owe",
         "SELECT COUNT(*) AS n FROM <asset> WHERE arrear_fee>0", ""),
        ("mnp.user_profile", "MNP 用户画像", "dwa_v_d_cus_cb_user_info",
         "SELECT * FROM <asset> WHERE user_id=:uid LIMIT 1", ""),
        ("mnp.user_charge", "MNP 用户费用", "dwa_v_m_cus_cb_sing_charge",
         "SELECT * FROM <asset> WHERE user_id=:uid LIMIT 1", ""),
        ("mnp.user_contracts", "MNP 用户合约", "dwa_v_d_cus_cb_act_info",
         "SELECT * FROM <asset> WHERE user_id=:uid", ""),
        ("mnp.user_queries", "MNP 用户携转查询", "dwd_d_cus_np_turn_query_user",
         "SELECT * FROM <asset> WHERE user_id=:uid", ""),
        ("mnp.user_maintains_by_device", "MNP 维挽（按号码）", "dwd_d_cus_qk_turn_maintain",
         "SELECT * FROM <asset> WHERE device_number=:device", ""),
        ("mnp.user_complaints_by_device", "MNP 工单（按号码）", "dwd_d_evt_kf_order_main",
         "SELECT * FROM <asset> WHERE device_number=:device", ""),
        ("mnp.user_voice_stats", "MNP 通话统计", "dwd_d_use_cb_f_voice",
         """SELECT COUNT(*) AS call_count,
                   COALESCE(SUM(call_duration),0) AS total_duration,
                   SUM(CASE WHEN oppose_dealer_type!=1 THEN 1 ELSE 0 END) AS cross_carrier_calls
            FROM <asset> WHERE user_id=:uid""", ""),
        ("mnp.user_owe_by_subs", "MNP 欠费（按 subs_id）", "dwd_m_mrt_al_chl_owe",
         "SELECT * FROM <asset> WHERE subs_id=:uid LIMIT 1", ""),
        ("mnp.maintain_by_reason", "MNP 维挽按原因", "dwd_d_cus_qk_turn_maintain",
         """SELECT turn_reason, COUNT(*) AS cnt,
                   SUM(CASE WHEN is_success_maintain='1' THEN 1 ELSE 0 END) AS success_cnt
            FROM <asset> GROUP BY turn_reason ORDER BY cnt DESC""", ""),
        ("mnp.maintain_by_product", "MNP 维挽按产品", "dwd_d_cus_qk_turn_maintain",
         """SELECT product_name, COUNT(*) AS cnt,
                   SUM(CASE WHEN is_success_maintain='1' THEN 1 ELSE 0 END) AS success_cnt
            FROM <asset> GROUP BY product_name ORDER BY cnt DESC""", ""),
        # MNP 风险用户 — 多表 JOIN（同 connection 内允许；显式 dependencies 列出所有依赖表）
        ("mnp.risk_users", "MNP 风险用户列表", "dwa_v_d_cus_cb_user_info",
         """SELECT
                u.user_id, u.device_number, u.area_id, u.user_status,
                u.innet_months, u.is_5g, u.pay_mode,
                COALESCE(c.total_fee, 0) AS arpu,
                COALESCE(owe.arrear_fee, 0) AS arrear_fee,
                q.query_time, q.query_channel, q.limit_remark, q.out_tag
            FROM dwa_v_d_cus_cb_user_info u
            LEFT JOIN dwa_v_m_cus_cb_sing_charge c ON u.user_id = c.user_id
            LEFT JOIN dwd_m_mrt_al_chl_owe owe ON u.user_id = owe.subs_id
            INNER JOIN dwd_d_cus_np_turn_query_user q ON u.user_id = q.user_id
            ORDER BY q.query_time DESC LIMIT 100""",
         "MNP 风险用户聚合视图（同库 JOIN）"),
    ]


# Broadband 表清单（仅注册 table Asset，业务 SQL 用 additional_asset_ids 模式跑动态 JOIN）
def _bb_tables() -> list[tuple[str, str]]:
    """(alias, table_name)"""
    return [
        ("bb.churn", "bb_install_churn"),
        ("bb.order", "bb_install_order"),
        ("bb.customer", "bb_customer"),
        ("bb.engineer", "bb_engineer"),
        ("bb.dispatch", "bb_dispatch_record"),
        ("bb.address", "bb_address"),
        ("bb.channel", "bb_channel"),
        ("bb.product", "bb_product"),
        ("bb.engineer_call", "bb_engineer_call"),
        ("bb.callback_call", "bb_callback_call"),
        ("bb.competitor_call", "bb_competitor_call"),
        ("bb.pending_pool", "bb_pending_pool"),
        ("bb.evidence", "bb_evidence"),
        ("bb.audit_trail", "bb_audit_trail"),
    ]


# ── 主入口 ───────────────────────────────────────────────

def seed(db: Session | None = None) -> dict:
    own = db is None
    if own:
        db = SessionLocal()
    stats = {"connections_created": 0, "table_assets_created": 0, "sql_views_created": 0}
    try:
        # 1. 仅查 Connection（用户需在"数据接入·连接"页提前创建）
        conn = _resolve_connection(db, _BB_CONN_NAME)
        if not conn:
            logger.info(
                "未发现业务连接「%s」，跳过业务资产 seed。"
                "请在前端「数据接入·连接」页创建该连接后重启，或调用 /api/v1/connections 创建。",
                _BB_CONN_NAME,
            )
            return stats

        # 2. base table Asset 注册（broadband + mnp 共用同一连接的不同表）
        asset_svc = AssetService(db)
        asset_repo = AssetRepository(db)
        all_tables = set(t[1] for t in _bb_tables())
        for _, _, base_t, _, _ in _mnp_seeds():
            all_tables.add(base_t)
        # 加上 broadband alias 表
        for alias, table in _bb_tables():
            existing_table = _find_table_asset(asset_repo, conn.id, table)
            if not existing_table:
                a = asset_svc.register(
                    name=table, alias=alias,
                    kind="table", connection_id=conn.id,
                    locator={"table": table},
                    description=f"业务表（自动注册）",
                )
                stats["table_assets_created"] += 1
                logger.info("注册 table Asset: %s", alias)
            else:
                if not existing_table.alias:
                    existing_table.alias = alias
                    db.commit()
        # mnp base tables 没专门 alias，按表名注册
        for _, _, base_t, _, _ in _mnp_seeds():
            existing = _find_table_asset(asset_repo, conn.id, base_t)
            if not existing:
                asset_svc.register(
                    name=base_t, kind="table", connection_id=conn.id,
                    locator={"table": base_t}, description="MNP 业务表（自动注册）",
                )
                stats["table_assets_created"] += 1

        # 3. mnp.* sql_view
        for alias, name, base_t, sql, desc in _mnp_seeds():
            existing = asset_repo.find_by_alias(alias)
            if existing:
                continue
            base = _find_table_asset(asset_repo, conn.id, base_t)
            if not base:
                logger.warning("base table %s 不存在，跳过 alias %s", base_t, alias)
                continue
            try:
                asset_svc.register(
                    name=name, alias=alias, kind="sql_view",
                    connection_id=conn.id,
                    locator={"base_asset_id": base.id, "sql": sql},
                    description=desc, cache_ttl_seconds=60,
                )
                stats["sql_views_created"] += 1
            except Exception:
                logger.exception("注册 sql_view 失败: %s", alias)

        return stats
    finally:
        if own:
            db.close()


# ── 内部工具 ────────────────────────────────────────────

def _resolve_connection(db: Session, name: str) -> Connection | None:
    return ConnectionRepository(db).find_by_name(name)


def _find_table_asset(repo: AssetRepository, conn_id: str, table_name: str) -> Asset | None:
    """按 connection + locator.table 查 table 资产（避免依赖 SQLite JSON 路径过滤）。"""
    candidates = [a for a in repo.list(connection_id=conn_id, kind="table")
                  if (a.locator or {}).get("table") == table_name]
    return candidates[0] if candidates else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    s = seed()
    print(s)
