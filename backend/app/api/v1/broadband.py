"""
宽带装机退单稽核 — 场景 API
数据源: 123.56.188.16:3306 / mnp_risk_warning (bb_* 表)
字段严格对齐本体设计规范(ONT_*)
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Any
import pymysql
import hashlib
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenes/broadband", tags=["broadband-audit"])

DB_CFG = dict(host="123.56.188.16", port=3306, user="bonc", password="bonc123",
              database="mnp_risk_warning", charset="utf8mb4")


def _conn():
    return pymysql.connect(**DB_CFG, cursorclass=pymysql.cursors.DictCursor)


def _query(sql: str, args=None) -> list[dict]:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchall()
    finally:
        conn.close()


def _query_one(sql: str, args=None) -> dict | None:
    rows = _query(sql, args)
    return rows[0] if rows else None


def _scalar(sql: str, args=None):
    r = _query_one(sql, args)
    return list(r.values())[0] if r else 0


def _ser(row: dict) -> dict:
    from datetime import datetime, date
    from decimal import Decimal
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v.isoformat()
        elif isinstance(v, Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out

# ── 响应模型 ──────────────────────────────────────────────

class OverviewResp(BaseModel):
    total: int = 0
    pending: int = 0
    analyzing: int = 0
    pending_todo: int = 0
    completed: int = 0
    error_count: int = 0
    accuracy_rate: float = 0.0
    avg_confidence: float = 0.0
    today_new: int = 0


class PaginatedList(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class StatsResp(BaseModel):
    cause_distribution: list[dict[str, Any]]
    subcategory_distribution: list[dict[str, Any]]
    trend_daily: list[dict[str, Any]]
    engineer_ranking: list[dict[str, Any]]
    channel_stats: list[dict[str, Any]]
    address_hotspots: list[dict[str, Any]]
    audit_status_distribution: list[dict[str, Any]]


# ── 接口 1: 稽核总览 KPI ─────────────────────────────────

@router.get("/overview", response_model=OverviewResp)
def broadband_overview():
    total = _scalar("SELECT COUNT(*) FROM bb_install_churn")
    status_counts = _query(
        "SELECT audit_status, COUNT(*) as cnt FROM bb_install_churn GROUP BY audit_status"
    )
    sc = {r["audit_status"]: r["cnt"] for r in status_counts}

    completed = sc.get("完成", 0)
    avg_conf = _scalar(
        "SELECT COALESCE(AVG(root_cause_confidence), 0) FROM bb_install_churn "
        "WHERE root_cause_confidence IS NOT NULL"
    )
    high_conf = _scalar(
        "SELECT COUNT(*) FROM bb_install_churn "
        "WHERE root_cause_confidence >= 0.85 AND audit_status='完成'"
    )
    accuracy = round(high_conf / completed, 4) if completed > 0 else 0

    today_new = _scalar(
        "SELECT COUNT(*) FROM bb_install_churn WHERE DATE(churn_time) = CURDATE()"
    )

    return OverviewResp(
        total=total,
        pending=sc.get("待稽核", 0),
        analyzing=sc.get("稽核中", 0),
        pending_todo=sc.get("挂起", 0),
        completed=completed,
        error_count=sc.get("失败", 0),
        accuracy_rate=round(accuracy, 4),
        avg_confidence=round(float(avg_conf), 4),
        today_new=today_new,
    )

# ── 接口 2: 退单稽核列表 ─────────────────────────────────

@router.get("/list", response_model=PaginatedList)
def broadband_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = Query(default=""),
    audit_status: str = Query(default=""),
    root_cause_level_one: str = Query(default=""),
    start_time: str = Query(default=""),
    end_time: str = Query(default=""),
):
    where_clauses = ["1=1"]
    args: list = []

    if keyword:
        where_clauses.append(
            "(c.churn_id LIKE %s OR o.order_no LIKE %s OR cu.customer_name LIKE %s OR o.install_address LIKE %s)"
        )
        kw = f"%{keyword}%"
        args.extend([kw, kw, kw, kw])
    if audit_status:
        where_clauses.append("c.audit_status = %s")
        args.append(audit_status)
    if root_cause_level_one:
        where_clauses.append("c.root_cause_level_one = %s")
        args.append(root_cause_level_one)
    if start_time:
        where_clauses.append("c.churn_time >= %s")
        args.append(start_time)
    if end_time:
        where_clauses.append("c.churn_time <= %s")
        args.append(end_time)

    where = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*) FROM bb_install_churn c
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        LEFT JOIN bb_customer cu ON o.cust_id = cu.customer_id
        WHERE {where}
    """
    total = _scalar(count_sql, args)

    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT c.churn_id, c.related_order_no, c.churn_time, c.churn_reason_text,
               c.churn_category_l1, c.churn_category_l2,
               c.audit_status, c.root_cause_code, c.root_cause_level_one,
               c.root_cause_level_two, c.root_cause_confidence,
               o.biz_type, o.install_address,
               cu.customer_name, cu.contact_phone,
               e.engineer_name
        FROM bb_install_churn c
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        LEFT JOIN bb_customer cu ON o.cust_id = cu.customer_id
        LEFT JOIN bb_engineer e ON o.engineer_id = e.engineer_id
        WHERE {where}
        ORDER BY c.churn_time DESC
        LIMIT %s OFFSET %s
    """
    rows = _query(data_sql, args + [page_size, offset])

    return PaginatedList(
        items=[_ser(r) for r in rows],
        total=total, page=page, page_size=page_size,
    )

# ── 接口 3: 退单详情 ─────────────────────────────────────

@router.get("/detail/{churn_id}")
def broadband_detail(churn_id: str):
    churn = _query_one("SELECT * FROM bb_install_churn WHERE churn_id = %s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")

    order = _query_one(
        "SELECT * FROM bb_install_order WHERE order_no = %s", (churn["related_order_no"],)
    )
    customer = _query_one(
        "SELECT * FROM bb_customer WHERE customer_id = %s", (order["cust_id"],)
    ) if order else None
    engineer = _query_one(
        "SELECT * FROM bb_engineer WHERE engineer_id = %s", (order["engineer_id"],)
    ) if order else None
    address = _query_one(
        "SELECT * FROM bb_address WHERE address_id = %s", (order["install_address_id"],)
    ) if order else None
    dispatch = _query_one(
        "SELECT * FROM bb_dispatch_record WHERE related_order_no = %s", (churn["related_order_no"],)
    )
    channel = _query_one(
        "SELECT * FROM bb_channel WHERE channel_id = %s", (order["channel_id"],)
    ) if order else None
    product = _query_one(
        "SELECT * FROM bb_product WHERE product_id = %s", (order["product_id"],)
    ) if order else None

    eng_calls = _query(
        "SELECT * FROM bb_engineer_call WHERE related_order_no = %s ORDER BY call_start_time",
        (churn["related_order_no"],)
    )
    cb_calls = _query(
        "SELECT * FROM bb_callback_call WHERE related_order_no = %s ORDER BY call_start_time",
        (churn["related_order_no"],)
    )
    comp_calls = _query(
        "SELECT * FROM bb_competitor_call WHERE customer_id = %s ORDER BY call_time",
        (order["cust_id"],)
    ) if order else []
    pending = _query(
        "SELECT * FROM bb_pending_pool WHERE order_no = %s", (churn["related_order_no"],)
    )

    # 计算通话汇总 (CallSummary - 衍生对象)
    call_summary = None
    if eng_calls:
        total_count = len(eng_calls)
        failed_count = sum(1 for c in eng_calls if c.get("connect_status") != "已接通")
        days = set()
        has_valid = False
        for c in eng_calls:
            if c.get("call_start_time"):
                days.add(c["call_start_time"].date() if hasattr(c["call_start_time"], 'date') else str(c["call_start_time"])[:10])
            if c.get("connect_status") == "已接通" and c.get("duration_seconds", 0) > 10:
                has_valid = True
        distinct_days = len(days)
        meets_threshold = distinct_days >= 2 and total_count >= 4 and failed_count >= 4
        call_summary = {
            "total_call_count": total_count,
            "failed_call_count": failed_count,
            "distinct_call_days": distinct_days,
            "has_valid_recording": has_valid,
            "meets_unreachable_threshold": meets_threshold,
        }

    return {
        "churn": _ser(churn),
        "order": _ser(order) if order else None,
        "customer": _ser(customer) if customer else None,
        "engineer": _ser(engineer) if engineer else None,
        "address": _ser(address) if address else None,
        "dispatch": _ser(dispatch) if dispatch else None,
        "channel": _ser(channel) if channel else None,
        "product": _ser(product) if product else None,
        "call_summary": call_summary,
        "engineer_calls": [_ser(c) for c in eng_calls],
        "callback_calls": [_ser(c) for c in cb_calls],
        "competitor_calls": [_ser(c) for c in comp_calls],
        "pending_pool": [_ser(p) for p in pending],
    }

# ── 接口 4: 统计分析 ─────────────────────────────────────

@router.get("/stats", response_model=StatsResp)
def broadband_stats():
    cause_dist = _query(
        "SELECT root_cause_level_one as name, COUNT(*) as value "
        "FROM bb_install_churn WHERE root_cause_level_one IS NOT NULL "
        "GROUP BY root_cause_level_one ORDER BY value DESC"
    )

    sub_dist = _query(
        "SELECT root_cause_level_two as name, root_cause_level_one as category, COUNT(*) as value "
        "FROM bb_install_churn WHERE root_cause_level_two IS NOT NULL "
        "GROUP BY root_cause_level_two, root_cause_level_one ORDER BY value DESC"
    )

    trend = _query(
        "SELECT DATE(churn_time) as date, COUNT(*) as count "
        "FROM bb_install_churn GROUP BY DATE(churn_time) ORDER BY date DESC LIMIT 30"
    )

    eng_rank = _query("""
        SELECT e.engineer_id, e.engineer_name, e.team_name, e.tech_level,
               e.employment_type, e.churn_rate_90d,
               COUNT(c.churn_id) as churn_count,
               SUM(CASE WHEN c.root_cause_level_one != c.churn_category_l1 THEN 1 ELSE 0 END) as false_report_count
        FROM bb_engineer e
        LEFT JOIN bb_install_order o ON e.engineer_id = o.engineer_id
        LEFT JOIN bb_install_churn c ON o.order_no = c.related_order_no
        WHERE c.churn_id IS NOT NULL
        GROUP BY e.engineer_id, e.engineer_name, e.team_name, e.tech_level,
                 e.employment_type, e.churn_rate_90d
        ORDER BY churn_count DESC LIMIT 15
    """)

    ch_stats = _query("""
        SELECT ch.channel_id, ch.channel_name, ch.channel_type,
               ch.hist_churn_rate, COUNT(c.churn_id) as churn_count
        FROM bb_channel ch
        LEFT JOIN bb_install_order o ON ch.channel_id = o.channel_id
        LEFT JOIN bb_install_churn c ON o.order_no = c.related_order_no
        WHERE c.churn_id IS NOT NULL
        GROUP BY ch.channel_id, ch.channel_name, ch.channel_type, ch.hist_churn_rate
        ORDER BY churn_count DESC
    """)

    addr_hot = _query("""
        SELECT a.community_name, a.resource_status, a.is_unconditional_accept,
               a.hist_churn_rate, COUNT(c.churn_id) as churn_count
        FROM bb_address a
        JOIN bb_install_order o ON a.address_id = o.install_address_id
        JOIN bb_install_churn c ON o.order_no = c.related_order_no
        GROUP BY a.community_name, a.resource_status, a.is_unconditional_accept, a.hist_churn_rate
        ORDER BY churn_count DESC LIMIT 15
    """)

    status_dist = _query(
        "SELECT audit_status as name, COUNT(*) as value "
        "FROM bb_install_churn GROUP BY audit_status ORDER BY value DESC"
    )

    return StatsResp(
        cause_distribution=[_ser(r) for r in cause_dist],
        subcategory_distribution=[_ser(r) for r in sub_dist],
        trend_daily=[_ser(r) for r in trend],
        engineer_ranking=[_ser(r) for r in eng_rank],
        channel_stats=[_ser(r) for r in ch_stats],
        address_hotspots=[_ser(r) for r in addr_hot],
        audit_status_distribution=[_ser(r) for r in status_dist],
    )


# ── 接口 5: 人工审核操作 ─────────────────────────────────

class AuditActionReq(BaseModel):
    action: str  # archive / override / flag_anomaly
    override_label: str | None = None
    reason: str | None = None


@router.post("/audit/{churn_id}")
def broadband_audit_action(churn_id: str, req: AuditActionReq):
    churn = _query_one("SELECT * FROM bb_install_churn WHERE churn_id = %s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")

    conn = _conn()
    try:
        with conn.cursor() as cur:
            if req.action == "archive":
                cur.execute(
                    "UPDATE bb_install_churn SET audit_status='完成', "
                    "manual_review_status='审核通过', archive_time=NOW(), "
                    "audit_completed_time=NOW() WHERE churn_id=%s",
                    (churn_id,)
                )
            elif req.action == "override":
                cur.execute(
                    "UPDATE bb_install_churn SET manual_review_status='已覆盖', "
                    "manual_override_label=%s, root_cause_confidence=1.0, "
                    "audit_status='完成', archive_time=NOW(), "
                    "audit_completed_time=NOW() WHERE churn_id=%s",
                    (req.override_label, churn_id)
                )
            elif req.action == "flag_anomaly":
                cur.execute(
                    "UPDATE bb_install_churn SET manual_review_status='审核驳回', "
                    "escalate_reason=%s WHERE churn_id=%s",
                    (req.reason or "证据异常", churn_id)
                )
            conn.commit()
    finally:
        conn.close()

    return {"ok": True, "churn_id": churn_id, "action": req.action}


# ── 写入辅助 ────────────────────────────────────────────

def _execute(sql: str, args=None):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


def _insert_trail(churn_id: str, event_type: str, event_detail: str, operator: str = "system"):
    tid = f"TRL{hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]}"
    _execute(
        "INSERT INTO bb_audit_trail (trail_id, churn_id, event_type, event_detail, operator) "
        "VALUES (%s, %s, %s, %s, %s)",
        (tid, churn_id, event_type, event_detail, operator)
    )


# ── 接口 6: 获取证据项 ─────────────────────────────────

@router.get("/detail/{churn_id}/evidence")
def get_evidence(churn_id: str):
    churn = _query_one("SELECT churn_id FROM bb_install_churn WHERE churn_id=%s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")
    rows = _query("SELECT * FROM bb_evidence WHERE churn_id=%s ORDER BY evidence_code", (churn_id,))
    return {"items": [_ser(r) for r in rows], "total": len(rows)}


# ── 接口 7: 稽核链路 ───────────────────────────────────

@router.get("/detail/{churn_id}/chain")
def get_audit_chain(churn_id: str):
    churn = _query_one("SELECT * FROM bb_install_churn WHERE churn_id=%s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")

    evidence = _query("SELECT * FROM bb_evidence WHERE churn_id=%s", (churn_id,))
    source_types = {}
    for e in evidence:
        st = e.get("source_type", "unknown")
        source_types[st] = source_types.get(st, 0) + 1

    nlp_evidence = [_ser(e) for e in evidence if e.get("evidence_type") == "nlp"]
    rule_evidence = [_ser(e) for e in evidence if e.get("evidence_type") == "rule"]
    hit_count = sum(1 for e in evidence if e.get("hit"))

    logic_hits = _query("SELECT * FROM bb_logic_hit WHERE churn_id=%s ORDER BY executed_at", (churn_id,))
    actions = _query("SELECT * FROM bb_audit_action WHERE churn_id=%s ORDER BY created_at", (churn_id,))

    hypothesis_scores = {}
    for lh in logic_hits:
        lf = lh.get("logic_function_id", "")
        if lf in ("LF-003", "LF-004"):
            delta = float(lh.get("confidence_delta", 0))
            hypothesis_scores[lf] = delta

    lf_ids = {lh["logic_function_id"] for lh in logic_hits}

    return {
        "perception": {
            "source_types": source_types,
            "total_sources": sum(source_types.values()),
            "lf_001_status": "completed" if "LF-001" in lf_ids else "pending",
        },
        "recognition": {
            "nlp_evidence": nlp_evidence,
            "rule_evidence": rule_evidence,
            "nlp_count": len(nlp_evidence),
            "rule_count": len(rule_evidence),
            "hit_count": hit_count,
            "lf_002_status": "completed" if "LF-002" in lf_ids else "pending",
            "lf_003_status": "completed" if "LF-003" in lf_ids else "pending",
        },
        "reasoning": {
            "logic_hits": [_ser(lh) for lh in logic_hits],
            "hypothesis_scores": hypothesis_scores,
            "lf_004_status": "completed" if "LF-004" in lf_ids else "pending",
            "lf_005_status": "completed" if "LF-005" in lf_ids else "pending",
        },
        "output": {
            "root_cause_code": churn.get("root_cause_code"),
            "root_cause_level_one": churn.get("root_cause_level_one"),
            "root_cause_level_two": churn.get("root_cause_level_two"),
            "root_cause_confidence": float(churn["root_cause_confidence"]) if churn.get("root_cause_confidence") else None,
            "actions": [_ser(a) for a in actions],
            "lf_007_status": "completed" if "LF-007" in lf_ids else "pending",
        },
    }


# ── 接口 8: 逻辑函数命中 ───────────────────────────────

@router.get("/detail/{churn_id}/logic-hits")
def get_logic_hits(churn_id: str):
    churn = _query_one("SELECT churn_id FROM bb_install_churn WHERE churn_id=%s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")
    rows = _query("SELECT * FROM bb_logic_hit WHERE churn_id=%s ORDER BY logic_function_id", (churn_id,))
    return {"items": [_ser(r) for r in rows], "total": len(rows)}


# ── 接口 9: 获取稽核动作 ───────────────────────────────

@router.get("/detail/{churn_id}/actions")
def get_actions(churn_id: str):
    churn = _query_one("SELECT churn_id FROM bb_install_churn WHERE churn_id=%s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")
    rows = _query("SELECT * FROM bb_audit_action WHERE churn_id=%s ORDER BY created_at", (churn_id,))
    return {"items": [_ser(r) for r in rows], "total": len(rows)}


# ── 接口 10: 审批通过 ──────────────────────────────────

class ApproveReq(BaseModel):
    approved_by: str = "admin"

@router.post("/detail/{churn_id}/actions/{action_id}/approve")
def approve_action(churn_id: str, action_id: str, req: ApproveReq):
    action = _query_one("SELECT * FROM bb_audit_action WHERE action_id=%s AND churn_id=%s", (action_id, churn_id))
    if not action:
        raise HTTPException(404, "动作不存在")
    if action["status"] != "pending_confirm":
        raise HTTPException(400, f"当前状态 {action['status']} 不可确认")
    _execute(
        "UPDATE bb_audit_action SET status='pending_feedback', approved_at=NOW(), approved_by=%s WHERE action_id=%s",
        (req.approved_by, action_id)
    )
    _insert_trail(churn_id, "action_confirmed", f"确认接受动作 {action['action_name']}", req.approved_by)
    return {"ok": True}


# ── 接口 11: 驳回 ──────────────────────────────────────

class RejectReq(BaseModel):
    rejected_by: str = "admin"
    reason: str = ""

@router.post("/detail/{churn_id}/actions/{action_id}/reject")
def reject_action(churn_id: str, action_id: str, req: RejectReq):
    action = _query_one("SELECT * FROM bb_audit_action WHERE action_id=%s AND churn_id=%s", (action_id, churn_id))
    if not action:
        raise HTTPException(404, "动作不存在")
    if action["status"] != "pending_confirm":
        raise HTTPException(400, f"当前状态 {action['status']} 不可驳回")
    _execute(
        "UPDATE bb_audit_action SET status='rejected', rejected_at=NOW(), rejected_by=%s, reject_reason=%s WHERE action_id=%s",
        (req.rejected_by, req.reason, action_id)
    )
    _insert_trail(churn_id, "action_rejected", f"驳回动作 {action['action_name']}: {req.reason}", req.rejected_by)
    return {"ok": True}


# ── 接口 11b: 确认接受动作 ─────────────────────────────

@router.post("/detail/{churn_id}/actions/{action_id}/confirm")
def confirm_action(churn_id: str, action_id: str):
    action = _query_one("SELECT * FROM bb_audit_action WHERE action_id=%s AND churn_id=%s", (action_id, churn_id))
    if not action:
        raise HTTPException(404, "动作不存在")
    if action["status"] != "pending_confirm":
        raise HTTPException(400, f"当前状态 {action['status']} 不可确认")
    _execute(
        "UPDATE bb_audit_action SET status='pending_feedback', approved_at=NOW(), approved_by='user' WHERE action_id=%s",
        (action_id,)
    )
    _insert_trail(churn_id, "action_confirmed", f"确认执行动作 {action['action_name']}", "user")
    return {"ok": True}


# ── 接口 11c: 提交动作反馈 ─────────────────────────────

class FeedbackReq(BaseModel):
    feedback_type: str = ""
    feedback_value: str = ""
    feedback_text: str = ""

@router.post("/detail/{churn_id}/actions/{action_id}/feedback")
def submit_feedback(churn_id: str, action_id: str, req: FeedbackReq):
    action = _query_one("SELECT * FROM bb_audit_action WHERE action_id=%s AND churn_id=%s", (action_id, churn_id))
    if not action:
        raise HTTPException(404, "动作不存在")
    if action["status"] != "pending_feedback":
        raise HTTPException(400, f"当前状态 {action['status']} 不可提交反馈")
    feedback_data = {
        "type": req.feedback_type,
        "value": req.feedback_value,
        "text": req.feedback_text,
    }
    _execute(
        "UPDATE bb_audit_action SET status='feedback_submitted', "
        "feedback_data=%s, feedback_time=NOW(), params_json=%s WHERE action_id=%s",
        (json.dumps(feedback_data, ensure_ascii=False),
         json.dumps(feedback_data, ensure_ascii=False), action_id)
    )
    _insert_trail(churn_id, "action_feedback",
                  f"动作 {action['action_name']} 反馈: {req.feedback_type}={req.feedback_value}", "user")

    # 检查该退单下所有待办是否都已处理，自动流转稽核状态
    remaining = _scalar(
        "SELECT COUNT(*) FROM bb_audit_action WHERE churn_id=%s AND status NOT IN ('feedback_submitted','rejected')",
        (churn_id,)
    )
    if remaining == 0:
        _execute(
            "UPDATE bb_install_churn SET audit_status='完成', archive_time=NOW() WHERE churn_id=%s",
            (churn_id,)
        )
        _insert_trail(churn_id, "audit_completed", "所有待办已处理，稽核自动完成", "system")

    return {"ok": True, "feedback_data": feedback_data}


# ── 接口 11d: 基于反馈触发二次归因 ──────────────────────

@router.post("/detail/{churn_id}/re-attribute")
def re_attribute(churn_id: str):
    churn = _query_one("SELECT * FROM bb_install_churn WHERE churn_id=%s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")

    completed_actions = _query(
        "SELECT * FROM bb_audit_action WHERE churn_id=%s AND status='feedback_submitted'", (churn_id,))
    if not completed_actions:
        raise HTTPException(400, "暂无已完成的动作反馈，无法触发二次归因")

    evidence = _query("SELECT * FROM bb_evidence WHERE churn_id=%s", (churn_id,))
    ev_map = {e["evidence_code"]: e for e in evidence}

    updated_evidences = []
    for act in completed_actions:
        feedback = json.loads(act["params_json"]) if act.get("params_json") else {}
        act_type = act.get("action_type_code", "")

        if act_type == "resource_check" and feedback.get("value"):
            has_resource = feedback["value"] == "有资源"
            e35_id = f"EV{hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]}"
            try:
                _execute(
                    "INSERT INTO bb_evidence (evidence_id, churn_id, evidence_code, evidence_type, "
                    "content, hit, confidence, raw_text) VALUES (%s,%s,'E35','manual',%s,%s,1.0,%s)",
                    (e35_id, churn_id,
                     "人工核实: " + ("有资源" if has_resource else "无资源"),
                     True, feedback.get("text", ""))
                )
                updated_evidences.append("E35")
            except Exception:
                pass

        elif act_type == "followup_call" and feedback.get("text"):
            e37_id = f"EV{hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]}"
            try:
                _execute(
                    "INSERT INTO bb_evidence (evidence_id, churn_id, evidence_code, evidence_type, "
                    "content, hit, confidence, raw_text) VALUES (%s,%s,'E37','manual',%s,1,0.9,%s)",
                    (e37_id, churn_id, "回访补全: " + feedback.get("value", ""), feedback["text"])
                )
                updated_evidences.append("E37")
            except Exception:
                pass

    _insert_trail(churn_id, "re_attribution",
                  f"触发二次归因，新增证据: {', '.join(updated_evidences)}", "system")

    return {
        "ok": True,
        "updated_evidences": updated_evidences,
        "message": f"二次归因完成，新增 {len(updated_evidences)} 条证据",
    }


# ── 接口 12: 智能收件箱 ────────────────────────────────

@router.get("/inbox")
def inbox_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action_type: str = Query(default=""),
    priority: str = Query(default=""),
    assignee: str = Query(default=""),
    status: str = Query(default="pending_confirm"),
):
    where = ["1=1"]
    args: list = []
    if status:
        where.append("a.status = %s")
        args.append(status)
    if action_type:
        where.append("a.action_type_code = %s")
        args.append(action_type)
    if priority:
        where.append("a.priority = %s")
        args.append(priority)
    if assignee:
        where.append("a.assignee LIKE %s")
        args.append(f"%{assignee}%")

    w = " AND ".join(where)
    total = _scalar(f"""
        SELECT COUNT(*) FROM bb_audit_action a
        LEFT JOIN bb_install_churn c ON a.churn_id = c.churn_id
        WHERE {w}
    """, args)

    offset = (page - 1) * page_size
    rows = _query(f"""
        SELECT a.*, c.churn_time, c.churn_reason_text, c.root_cause_level_one,
               c.root_cause_confidence, cu.customer_name
        FROM bb_audit_action a
        LEFT JOIN bb_install_churn c ON a.churn_id = c.churn_id
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        LEFT JOIN bb_customer cu ON o.cust_id = cu.customer_id
        WHERE {w}
        ORDER BY FIELD(a.priority, 'high','medium','low'), a.created_at DESC
        LIMIT %s OFFSET %s
    """, args + [page_size, offset])

    return {"items": [_ser(r) for r in rows], "total": total, "page": page, "page_size": page_size}


# ── 接口 13: 批量审批 ──────────────────────────────────

class BatchApproveReq(BaseModel):
    action_ids: list[str]
    approved_by: str = "admin"

@router.post("/inbox/batch-approve")
def batch_approve(req: BatchApproveReq):
    if not req.action_ids:
        raise HTTPException(400, "action_ids不能为空")
    count = 0
    for aid in req.action_ids:
        action = _query_one("SELECT * FROM bb_audit_action WHERE action_id=%s AND status='pending_confirm'", (aid,))
        if action:
            _execute(
                "UPDATE bb_audit_action SET status='pending_feedback', approved_at=NOW(), approved_by=%s WHERE action_id=%s",
                (req.approved_by, aid)
            )
            _insert_trail(action["churn_id"], "action_confirmed", f"批量确认接受 {action['action_name']}", req.approved_by)
            count += 1
    return {"ok": True, "approved_count": count}


# ── 接口 14: 执行工作台 ────────────────────────────────

@router.get("/workbench")
def workbench_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str = Query(default=""),
):
    where = ["a.status IN ('pending_feedback','feedback_submitted','rejected')"]
    args: list = []
    if status:
        where.append("a.status = %s")
        args.append(status)

    w = " AND ".join(where)
    total = _scalar(f"SELECT COUNT(*) FROM bb_audit_action a WHERE {w}", args)
    offset = (page - 1) * page_size
    rows = _query(f"""
        SELECT a.*, c.churn_time, c.root_cause_level_one, cu.customer_name,
               (SELECT COUNT(*) FROM bb_action_execution e WHERE e.action_id = a.action_id) as exec_count
        FROM bb_audit_action a
        LEFT JOIN bb_install_churn c ON a.churn_id = c.churn_id
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        LEFT JOIN bb_customer cu ON o.cust_id = cu.customer_id
        WHERE {w}
        ORDER BY a.approved_at DESC
        LIMIT %s OFFSET %s
    """, args + [page_size, offset])
    return {"items": [_ser(r) for r in rows], "total": total, "page": page, "page_size": page_size}


# ── 接口 15: 执行详情 ──────────────────────────────────

@router.get("/workbench/{action_id}/execution")
def execution_detail(action_id: str):
    action = _query_one("SELECT * FROM bb_audit_action WHERE action_id=%s", (action_id,))
    if not action:
        raise HTTPException(404, "动作不存在")
    executions = _query(
        "SELECT * FROM bb_action_execution WHERE action_id=%s ORDER BY started_at", (action_id,)
    )
    return {"action": _ser(action), "executions": [_ser(e) for e in executions]}


# ── 接口 16: 审计追踪 ──────────────────────────────────

@router.get("/detail/{churn_id}/trail")
def get_audit_trail(churn_id: str):
    rows = _query(
        "SELECT * FROM bb_audit_trail WHERE churn_id=%s ORDER BY created_at DESC", (churn_id,)
    )
    return {"items": [_ser(r) for r in rows], "total": len(rows)}


# ── 接口 17: SSE 实时分析 ──────────────────────────────

from fastapi.responses import StreamingResponse
import time


def _sse_event(step: str, status: str, message: str = "", data: Any = None) -> str:
    import json as _json
    payload = {"step": step, "status": status, "message": message}
    if data is not None:
        payload["data"] = data
    return f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"


# PLACEHOLDER_ANALYSIS_STREAM


def _mask_phone(phone: str) -> str:
    if not phone or len(phone) < 7:
        return phone or ""
    return phone[:3] + "****" + phone[-4:]


def _make_todos(churn_id: str, churn: dict, evidence: list[dict],
                root_cause_l1: str | None, order: dict | None,
                customer: dict | None, address: dict | None) -> list[dict]:
    """根据证据和归因结果条件生成待办动作（参考 poc-service-api 的 _check_todo_conditions）"""
    todos: list[dict] = []
    ev_map = {e.get("evidence_code", ""): e for e in evidence}

    customer_name = (customer or {}).get("customer_name", "")
    contact_phone = (customer or {}).get("contact_phone", "")
    masked_phone = _mask_phone(contact_phone)
    order_no = churn.get("related_order_no", "")
    related_info = f"{order_no} · {customer_name} {masked_phone}".strip(" ·")

    # ── resource_check: E28命中 + (E1或E2命中) + 地址资源状态未知 ──
    e28 = ev_map.get("E28")
    e1, e2 = ev_map.get("E1"), ev_map.get("E2")
    resource_status = (address or {}).get("resource_status", "")
    if (e28 and e28.get("hit")
            and ((e1 and e1.get("hit")) or (e2 and e2.get("hit")))
            and resource_status not in ("是", "否")):
        address_text = (order or {}).get("install_address", order_no)
        aid = f"ACT{hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]}"
        todos.append({
            "action_id": aid, "churn_id": churn_id,
            "todo_type": "resource_check",
            "action_type_code": "resource_check",
            "action_name": f"地址网络资源核实 — {address_text}",
            "description": "系统预判有资源，工程师反馈现场无资源，需人工核实地址库数据与现场实际是否一致。",
            "priority": "medium",
            "status": "pending_confirm",
            "trigger_rule": "E28(预判有资源) AND (E1|E2)(工程师反馈无资源) AND address.resource_status == null",
            "expected_effect": "核实结果回写地址对象 → 若实际无资源则R类假设激活 → 根因可能变更",
            "support_evidences": [
                {"code": "E28", "name": "预判有资源", "role": "support"},
                {"code": "E35", "name": "实际资源(待核实)", "role": "refute"},
            ],
            "display_data": {"address_text": address_text, "address_id": (order or {}).get("install_address_id", "")},
            "related_info": related_info,
            "assignee": None, "params_json": None,
            "feedback_data": None, "feedback_time": None,
        })

    # ── followup_call: 归因结果与退单原因不一致时才需回访核实 ──
    churn_category = churn.get("churn_category_l1") or ""
    if root_cause_l1 and root_cause_l1 != churn_category:
        aid = f"ACT{hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]}"
        churn_time_str = str(churn.get("churn_time", ""))[:16]
        todos.append({
            "action_id": aid, "churn_id": churn_id,
            "todo_type": "followup_call",
            "action_type_code": "followup_call",
            "action_name": "中台外呼回访 — 退单原因核实",
            "description": f"退单原因为「{churn_category or '未填写'}」，稽核推理根因为「{root_cause_l1}」，两者不一致，需中台回访客户核实真实退单原因。",
            "priority": "high",
            "status": "pending_confirm",
            "trigger_rule": "attribution.root_cause ≠ churn.reported_reason → TRIGGER_CALLBACK",
            "expected_effect": "回访结果回写 → 触发增量推理 → 提升置信度可靠性",
            "support_evidences": [
                e for e in [
                    {"code": "E1", "name": "工程师反馈无资源", "role": "support"} if ev_map.get("E1", {}).get("hit") else None,
                    {"code": "E3", "name": "用户主动取消", "role": "support"} if ev_map.get("E3", {}).get("hit") else None,
                    {"code": "E4", "name": "用户情绪负面", "role": "support"} if ev_map.get("E4", {}).get("hit") else None,
                ] if e is not None
            ],
            "display_data": {
                "customer_name": customer_name, "masked_phone": masked_phone,
                "order_id": order_no, "churn_time": churn_time_str,
            },
            "related_info": related_info,
            "assignee": None, "params_json": None,
            "feedback_data": None, "feedback_time": None,
        })

    # ── secondary_marketing: E36命中(异网通话频次高) ──
    e36 = ev_map.get("E36")
    if e36 and e36.get("hit"):
        aid = f"ACT{hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]}"
        todos.append({
            "action_id": aid, "churn_id": churn_id,
            "todo_type": "secondary_marketing",
            "action_type_code": "secondary_marketing",
            "action_name": "二次营销 — 客户挽留",
            "description": "检测到客户存在异网通话记录，存在携转风险，建议进行二次营销挽留。",
            "priority": "low",
            "status": "pending_confirm",
            "trigger_rule": "E36(异网通话频次高) → TRIGGER_MARKETING",
            "expected_effect": "营销外呼 → 客户挽留 → 降低携转流失率",
            "support_evidences": [
                {"code": "E36", "name": "竞争对手通话频次高", "role": "support"},
            ],
            "display_data": {
                "customer_name": customer_name, "masked_phone": masked_phone,
                "product_name": (order or {}).get("product_name", ""),
            },
            "related_info": related_info,
            "assignee": None, "params_json": None,
            "feedback_data": None, "feedback_time": None,
        })

    return todos


def _analysis_stream(churn_id: str):
    churn = _query_one("SELECT * FROM bb_install_churn WHERE churn_id=%s", (churn_id,))
    if not churn:
        yield _sse_event("error", "error", "退单记录不存在")
        return

    _execute("UPDATE bb_install_churn SET audit_status='稽核中' WHERE churn_id=%s", (churn_id,))

    # ── Step 1: 感知 — 数据采集 ──
    yield _sse_event("perception", "start", "开始数据采集...")
    time.sleep(0.3)

    order = _query_one(
        "SELECT * FROM bb_install_order WHERE order_no=%s", (churn["related_order_no"],)
    )
    customer = _query_one(
        "SELECT * FROM bb_customer WHERE customer_id=%s", (order["cust_id"],)
    ) if order else None
    engineer = _query_one(
        "SELECT * FROM bb_engineer WHERE engineer_id=%s", (order["engineer_id"],)
    ) if order else None
    address = _query_one(
        "SELECT * FROM bb_address WHERE address_id=%s", (order["install_address_id"],)
    ) if order else None
    dispatch = _query_one(
        "SELECT * FROM bb_dispatch_record WHERE related_order_no=%s", (churn["related_order_no"],)
    )
    channel = _query_one(
        "SELECT * FROM bb_channel WHERE channel_id=%s", (order["channel_id"],)
    ) if order else None
    product = _query_one(
        "SELECT * FROM bb_product WHERE product_id=%s", (order["product_id"],)
    ) if order else None

    source_types = {}
    for label, obj in [("工单", order), ("客户", customer), ("工程师", engineer),
                       ("地址", address), ("派单", dispatch), ("渠道", channel), ("产品", product)]:
        if obj:
            source_types[label] = 1

    eng_calls = _query(
        "SELECT * FROM bb_engineer_call WHERE related_order_no=%s", (churn["related_order_no"],)
    )
    cb_calls = _query(
        "SELECT * FROM bb_callback_call WHERE related_order_no=%s", (churn["related_order_no"],)
    )
    comp_calls = _query(
        "SELECT * FROM bb_competitor_call WHERE customer_id=%s", (order["cust_id"],)
    ) if order else []

    if eng_calls:
        source_types["工程师通话"] = len(eng_calls)
    if cb_calls:
        source_types["回访通话"] = len(cb_calls)
    if comp_calls:
        source_types["异网通话"] = len(comp_calls)

    yield _sse_event("perception", "complete", f"采集完成，共 {sum(source_types.values())} 条数据源",
                     {"source_types": source_types, "total_sources": sum(source_types.values())})
    time.sleep(0.3)

    # ── Step 2: 识别 — 证据提取 ──
    yield _sse_event("recognition", "start", "开始证据提取...")
    time.sleep(0.3)

    evidence = _query("SELECT * FROM bb_evidence WHERE churn_id=%s", (churn_id,))
    nlp_evidence = [_ser(e) for e in evidence if e.get("evidence_type") == "nlp"]
    rule_evidence = [_ser(e) for e in evidence if e.get("evidence_type") == "rule"]
    hit_count = sum(1 for e in evidence if e.get("hit"))

    yield _sse_event("recognition", "progress", f"NLP证据 {len(nlp_evidence)} 条，规则证据 {len(rule_evidence)} 条")
    time.sleep(0.2)
    yield _sse_event("recognition", "complete", f"证据提取完成，命中 {hit_count} 条", {
        "nlp_count": len(nlp_evidence), "rule_count": len(rule_evidence),
        "hit_count": hit_count, "evidences": nlp_evidence + rule_evidence,
    })
    time.sleep(0.3)

    # PLACEHOLDER_STREAM_PART2

    # ── Step 3: 推理 — 逻辑命中 ──
    yield _sse_event("reasoning", "start", "开始逻辑推理...")
    time.sleep(0.3)

    logic_hits = _query("SELECT * FROM bb_logic_hit WHERE churn_id=%s ORDER BY executed_at", (churn_id,))
    hypothesis_scores = {}
    for lh in logic_hits:
        lf = lh.get("logic_function_id", "")
        if lf in ("LF-003", "LF-004"):
            hypothesis_scores[lf] = float(lh.get("confidence_delta", 0))

    yield _sse_event("reasoning", "complete", f"逻辑推理完成，命中 {len(logic_hits)} 条规则", {
        "logic_hits": [_ser(lh) for lh in logic_hits],
        "hypothesis_scores": hypothesis_scores,
    })
    time.sleep(0.3)

    # ── Step 4: 归因 — 结论输出 ──
    yield _sse_event("attribution", "start", "生成归因结论...")
    time.sleep(0.3)

    root_cause_code = churn.get("root_cause_code")
    root_cause_l1 = churn.get("root_cause_level_one")
    root_cause_l2 = churn.get("root_cause_level_two")
    confidence = float(churn["root_cause_confidence"]) if churn.get("root_cause_confidence") else None

    # 如果尚无归因结论，根据证据命中情况计算
    if not root_cause_l1:
        CAUSE_EVIDENCE_MAP = {
            "用户原因": ["E1","E2","E3","E4","E5","E6","E7","E8","E21","E32","E33","E34","E36"],
            "施工原因": ["E9","E10","E11","E12","E13","E14","E17","E18","E22","E27","E28"],
            "资源原因": ["E19","E20","E23","E29","E30","E31","E35"],
            "业务原因": ["E5","E8","E32","E33"],
        }
        L2_MAP = {
            "用户原因": ["用户不想装","联系不上用户","已选友商","实名认证问题","支付/金融问题","用户要求变更"],
            "施工原因": ["入户线问题","施工受阻(物业/房东)","智家人员问题","无法攻克技术问题"],
            "资源原因": ["建设时间长","非无条件受理区域","无资源覆盖","待装无建设计划","资源不足/故障","垄断小区"],
            "业务原因": ["资费疑问","办理条件限制","重复单","未申请业务","受理信息错误","业务规则限制","测试单","渠道权限不足"],
        }

        hit_codes = {e["evidence_code"] for e in evidence if e.get("hit")}
        cause_scores = {}
        for cause, codes in CAUSE_EVIDENCE_MAP.items():
            cause_scores[cause] = len(hit_codes & set(codes))

        best_l1 = max(cause_scores, key=cause_scores.get)
        best_score = cause_scores[best_l1]

        if best_score > 0:
            total_hit = sum(cause_scores.values()) or 1
            confidence = round(min(0.5 + best_score / total_hit * 0.5, 0.99), 4)

            # 根据退单原因文本匹配最佳 L2
            churn_text = churn.get("churn_reason_text", "")
            cat_l2 = churn.get("churn_category_l2", "")
            root_cause_l2 = None
            for l2 in L2_MAP[best_l1]:
                if l2 in churn_text or l2 == cat_l2:
                    root_cause_l2 = l2
                    break
            if not root_cause_l2:
                root_cause_l2 = L2_MAP[best_l1][0]

            root_cause_l1 = best_l1
            root_cause_code = f"{best_l1[0]}{L2_MAP[best_l1].index(root_cause_l2)+1}"
        else:
            # 无命中证据时，回退到退单分类
            root_cause_l1 = churn.get("churn_category_l1")
            root_cause_l2 = churn.get("churn_category_l2")
            confidence = 0.5
            if root_cause_l1 and root_cause_l2 and root_cause_l1 in L2_MAP:
                idx = L2_MAP[root_cause_l1].index(root_cause_l2) + 1 if root_cause_l2 in L2_MAP[root_cause_l1] else 1
                root_cause_code = f"{root_cause_l1[0]}{idx}"
            else:
                root_cause_code = None

        # 写回数据库（只写根因字段，状态由 todo 生成结果决定）
        if root_cause_l1:
            _execute(
                "UPDATE bb_install_churn SET root_cause_code=%s, root_cause_level_one=%s, "
                "root_cause_level_two=%s, root_cause_confidence=%s WHERE churn_id=%s",
                (root_cause_code, root_cause_l1, root_cause_l2, confidence, churn_id)
            )

    conclusion_parts = []
    if root_cause_l1:
        conclusion_parts.append(f"根因类别: {root_cause_l1}")
    if root_cause_l2:
        conclusion_parts.append(f"根因细类: {root_cause_l2}")
    if root_cause_code:
        conclusion_parts.append(f"根因编码: {root_cause_code}")
    if confidence is not None:
        conclusion_parts.append(f"置信度: {confidence * 100:.1f}%")

    conclusion = "\n".join(conclusion_parts) if conclusion_parts else "暂无归因结论"

    for i in range(0, len(conclusion), 4):
        chunk = conclusion[i:i+4]
        yield _sse_event("attribution", "streaming", "", chunk)
        time.sleep(0.05)

    actions = _query("SELECT * FROM bb_audit_action WHERE churn_id=%s ORDER BY created_at", (churn_id,))
    yield _sse_event("attribution", "complete", "归因分析完成", {
        "root_cause_code": root_cause_code,
        "root_cause_level_one": root_cause_l1,
        "root_cause_level_two": root_cause_l2,
        "root_cause_confidence": confidence,
        "churn_reason_text": churn.get("churn_reason_text"),
        "churn_category_l1": churn.get("churn_category_l1"),
        "churn_category_l2": churn.get("churn_category_l2"),
        "actions": [_ser(a) for a in actions],
    })
    time.sleep(0.2)

    # ── Step 5: 动作生成 — 基于证据和归因条件生成待办 ──
    yield _sse_event("todo", "start", "正在生成推荐动作...")
    time.sleep(0.3)

    evidence_raw = _query("SELECT * FROM bb_evidence WHERE churn_id=%s", (churn_id,))
    todos = _make_todos(churn_id, churn, [_ser(e) for e in evidence_raw],
                        root_cause_l1, order, customer, address)

    for todo in todos:
        try:
            _execute(
                "INSERT INTO bb_audit_action "
                "(action_id, churn_id, action_type_code, todo_type, action_name, description, "
                "priority, status, assignee, params_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (todo["action_id"], churn_id, todo["action_type_code"],
                 todo.get("todo_type", todo["action_type_code"]),
                 todo["action_name"], todo["description"],
                 todo["priority"], todo["status"], todo.get("assignee"),
                 json.dumps(todo.get("params_json"), ensure_ascii=False) if todo.get("params_json") else None)
            )
        except Exception:
            pass
        yield _sse_event("todo", "progress", f"待办：{todo['action_name']}", todo)
        time.sleep(0.15)

    yield _sse_event("todo", "complete",
                     f"共生成 {len(todos)} 个推荐动作" if todos else "无需生成动作",
                     {"todos": todos, "count": len(todos)})

    if todos:
        _execute("UPDATE bb_install_churn SET audit_status='挂起' WHERE churn_id=%s", (churn_id,))
    else:
        _execute("UPDATE bb_install_churn SET audit_status='完成', archive_time=NOW() WHERE churn_id=%s", (churn_id,))

    yield _sse_event("done", "complete", "分析完成")


@router.post("/analyze/{churn_id}")
def analyze_churn(churn_id: str):
    def _safe_stream():
        try:
            yield from _analysis_stream(churn_id)
        except Exception as e:
            logger.exception("分析流程异常: %s", e)
            _execute("UPDATE bb_install_churn SET audit_status='失败' WHERE churn_id=%s", (churn_id,))
            yield _sse_event("error", "error", f"分析异常: {e}")
    return StreamingResponse(
        _safe_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# PLACEHOLDER_ONTOLOGY_GRAPH


# ── 接口 18: 本体图谱数据 ──────────────────────────────

@router.get("/detail/{churn_id}/ontology-graph")
def get_ontology_graph(churn_id: str):
    churn = _query_one("SELECT * FROM bb_install_churn WHERE churn_id=%s", (churn_id,))
    if not churn:
        raise HTTPException(404, "退单记录不存在")

    order = _query_one(
        "SELECT * FROM bb_install_order WHERE order_no=%s", (churn["related_order_no"],)
    )

    nodes = []
    edges = []

    nodes.append({
        "id": churn["churn_id"], "type": "refund", "name": f"退单 {churn['churn_id'][-6:]}",
        "attributes": {"churn_reason": churn.get("churn_reason_text"),
                       "audit_status": churn.get("audit_status"),
                       "root_cause": churn.get("root_cause_level_one")},
    })

    if order:
        nodes.append({
            "id": order["order_no"], "type": "order",
            "name": f"工单 {order['order_no'][-6:]}",
            "attributes": {"biz_type": order.get("biz_type"),
                           "product_name": order.get("product_name"),
                           "order_status": order.get("order_status")},
        })
        edges.append({"source": churn["churn_id"], "target": order["order_no"],
                       "relation": "关联工单"})

        if order.get("cust_id"):
            customer = _query_one("SELECT * FROM bb_customer WHERE customer_id=%s",
                                  (order["cust_id"],))
            if customer:
                nodes.append({
                    "id": customer["customer_id"], "type": "customer",
                    "name": customer.get("customer_name", "客户"),
                    "attributes": {"customer_level": customer.get("customer_level"),
                                   "network_age": customer.get("network_age")},
                })
                edges.append({"source": order["order_no"],
                               "target": customer["customer_id"], "relation": "所属客户"})

        if order.get("engineer_id"):
            engineer = _query_one("SELECT * FROM bb_engineer WHERE engineer_id=%s",
                                  (order["engineer_id"],))
            if engineer:
                nodes.append({
                    "id": engineer["engineer_id"], "type": "engineer",
                    "name": engineer.get("engineer_name", "工程师"),
                    "attributes": {"team_name": engineer.get("team_name"),
                                   "tech_level": engineer.get("tech_level")},
                })
                edges.append({"source": order["order_no"],
                               "target": engineer["engineer_id"], "relation": "施工工程师"})

                eng_calls = _query(
                    "SELECT * FROM bb_engineer_call WHERE related_order_no=%s LIMIT 3",
                    (churn["related_order_no"],))
                for i, c in enumerate(eng_calls):
                    cid = c.get("call_id", f"ECALL-{i}")
                    nodes.append({
                        "id": cid, "type": "call", "name": f"通话{i+1}",
                        "attributes": {"connect_status": c.get("connect_status"),
                                       "duration": c.get("duration_seconds")},
                    })
                    edges.append({"source": engineer["engineer_id"], "target": cid,
                                   "relation": "外呼"})

        if order.get("install_address_id"):
            address = _query_one("SELECT * FROM bb_address WHERE address_id=%s",
                                 (order["install_address_id"],))
            if address:
                nodes.append({
                    "id": address["address_id"], "type": "address",
                    "name": address.get("community_name") or
                            (address.get("standard_address", "地址") or "地址")[:10],
                    "attributes": {"resource_status": address.get("resource_status"),
                                   "is_unconditional": address.get("is_unconditional_accept")},
                })
                edges.append({"source": order["order_no"],
                               "target": address["address_id"], "relation": "装机地址"})

        if order.get("channel_id"):
            channel = _query_one("SELECT * FROM bb_channel WHERE channel_id=%s",
                                 (order["channel_id"],))
            if channel:
                nodes.append({
                    "id": channel["channel_id"], "type": "channel",
                    "name": channel.get("channel_name", "渠道"),
                    "attributes": {"channel_type": channel.get("channel_type")},
                })
                edges.append({"source": order["order_no"],
                               "target": channel["channel_id"], "relation": "受理渠道"})

        if order.get("product_id"):
            product = _query_one("SELECT * FROM bb_product WHERE product_id=%s",
                                 (order["product_id"],))
            if product:
                nodes.append({
                    "id": product["product_id"], "type": "product",
                    "name": product.get("product_name", "产品"),
                    "attributes": {"product_type": product.get("product_type"),
                                   "speed_level": product.get("speed_level")},
                })
                edges.append({"source": order["order_no"],
                               "target": product["product_id"], "relation": "订购产品"})

    dispatch = _query_one(
        "SELECT * FROM bb_dispatch_record WHERE related_order_no=%s",
        (churn["related_order_no"],))
    if dispatch:
        did = dispatch.get("dispatch_id", f"DSP-{churn['related_order_no']}")
        nodes.append({
            "id": did, "type": "dispatch", "name": "派单记录",
            "attributes": {"dispatch_status": dispatch.get("dispatch_status"),
                           "late_minutes": dispatch.get("late_duration_minutes")},
        })
        if order:
            edges.append({"source": order["order_no"], "target": did, "relation": "派单"})

    return {"nodes": nodes, "edges": edges}


# ── 语音质检 ──────────────────────────────────────────────────

class VoiceAuditReq(BaseModel):
    calls: list[dict]  # [{call_id, call_type, asr_text, engineer_name?}]

@router.post("/detail/{churn_id}/voice-audit")
def voice_audit(churn_id: str, req: VoiceAuditReq):
    from openai import OpenAI
    from app.config import settings

    client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_API_BASE)

    results = []
    for call in req.calls:
        asr = (call.get("asr_text") or "").strip()
        if not asr:
            results.append({"call_id": call.get("call_id"), "skipped": True, "reason": "无ASR文本"})
            continue

        prompt = f"""你是宽带装机服务质检专家。请对以下工程师与客户的通话文本进行质检分析。

通话文本：
{asr}

请从以下5个维度逐一评分（pass/fail）并给出简短说明：
1. 自我介绍：工程师是否进行了规范的自我介绍（姓名、工号、来意）
2. 问题确认：是否清晰确认了客户问题或退单原因
3. 操作规范：是否按规范流程操作，有无违规承诺或误导性表述
4. 情绪处理：面对客户投诉/不满时是否妥善安抚
5. 结果告知：是否明确告知处理结果或后续安排

返回JSON格式：
{{
  "overall": "pass" | "fail" | "warning",
  "score": 0-100,
  "summary": "一句话总结",
  "dimensions": [
    {{"name": "自我介绍", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "问题确认", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "操作规范", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "情绪处理", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "结果告知", "result": "pass"|"fail"|"na", "comment": "..."}}
  ],
  "risk_flags": ["..."]
}}
只返回JSON，不要其他内容。"""

        try:
            resp = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            audit = json.loads(raw)
            audit["call_id"] = call.get("call_id")
            audit["call_type"] = call.get("call_type", "engineer")
            results.append(audit)
        except Exception as e:
            results.append({"call_id": call.get("call_id"), "error": str(e), "overall": "error"})

    return {"results": results}
