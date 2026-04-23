"""
内置 Skill 执行器 — 将场景验证的业务逻辑封装为可复用的 skill 函数
每个 skill 函数签名: (params: dict, db: Session) -> dict
返回统一格式: { success: bool, summary: str, data: dict }
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import OntologyEntity, DataSource, BusinessRule
from app.services.datasource_utils import execute_readonly_sql
from app.services.rule_engine import RuleEvaluator

logger = logging.getLogger(__name__)

SKILL_REGISTRY: dict[str, callable] = {}


def register_skill(code_ref: str):
    def decorator(fn):
        SKILL_REGISTRY[code_ref] = fn
        return fn
    return decorator


def execute_skill(code_ref: str, params: dict, db: Session) -> dict:
    fn = SKILL_REGISTRY.get(code_ref)
    if not fn:
        return {"success": False, "summary": f"未知 skill: {code_ref}", "data": {}}
    try:
        return fn(params, db)
    except Exception as e:
        logger.error(f"Skill {code_ref} 执行失败: {e}")
        return {"success": False, "summary": f"执行失败: {e}", "data": {}}


# ── 携号转网风险评估 ──────────────────────────────────────

_NS = "s5"
_ENTITY_ALIAS = {
    "CbssSubscriber": "MobileSubscriber",
    "MnpEligibilityQuery": "PortabilityQuery",
    "SubscriberContract": "UserContract",
    "CustomerComplaint": "ComplaintWorkOrder",
    "NetworkQuality": "MonthlyBilling",
    "CompetitorActivity": "VoiceCallRecord",
    "FamilyGroup": "ConvergencePackage",
    "MnpRiskUser": "RetentionRecord",
}
_MNP_ENTITIES = list(_ENTITY_ALIAS.keys())


def _get_entity_and_ds(db: Session, entity_name: str):
    db_name = _ENTITY_ALIAS.get(entity_name, entity_name)
    entity = db.query(OntologyEntity).filter(OntologyEntity.id == f"{_NS}_{db_name}").first()
    if not entity:
        entity = db.query(OntologyEntity).filter(OntologyEntity.name == db_name).first()
    if not entity:
        entity = db.query(OntologyEntity).filter(OntologyEntity.id == f"{_NS}_{entity_name}").first()
    if not entity:
        return None, None
    ds_ref = (entity.schema_json or {}).get("datasource_ref", "")
    if not ds_ref:
        return entity, None
    ds = db.query(DataSource).filter(DataSource.name == ds_ref, DataSource.enabled == True).first()
    return entity, ds


def _query_user_row(db: Session, entity_name: str, user_id: str, device_number: str = "") -> dict:
    entity, ds = _get_entity_and_ds(db, entity_name)
    if not entity or not ds or not ds.table_name:
        return {}
    pk_field = (entity.schema_json or {}).get("primary_key", "user_id")
    if pk_field in ("sheet_id",) and device_number:
        where = f"device_number = '{device_number}'"
    elif pk_field == "device_number" and device_number:
        where = f"device_number = '{device_number}'"
    elif pk_field == "subs_id":
        where = f"subs_id = '{user_id}'"
    else:
        where = f"{pk_field} = '{user_id}'"
    sql = f"SELECT * FROM {ds.table_name} WHERE {where} LIMIT 1"
    result = execute_readonly_sql(ds, sql, limit=1)
    if result.get("error") or not result.get("rows"):
        return {}
    columns = result["columns"]
    row = result["rows"][0]
    return {columns[i]: row[i] for i in range(len(columns))}


def _serialize(val: Any) -> Any:
    from datetime import date, datetime as dt
    from decimal import Decimal
    if isinstance(val, (date, dt)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val


def _calc_risk_score(eval_result: dict) -> int:
    results = eval_result.get("results", [])
    if not results:
        return 0
    total_matched = 0
    total_conditions = 0
    risk_weight = {"high": 3, "medium": 2, "low": 1}
    for r in results:
        weight = risk_weight.get(r.get("risk_level", ""), 1)
        total_matched += r.get("matched_count", 0) * weight
        total_conditions += r.get("total_count", 0) * weight
    if total_conditions == 0:
        return 0
    return min(100, int((total_matched / total_conditions) * 100))


def _analyze_churn_reasons(entities: dict) -> list[str]:
    reasons = []
    contract = entities.get("SubscriberContract", {})
    if contract.get("end_date"):
        reasons.append("合约即将到期")
    complaint = entities.get("CustomerComplaint", {})
    count_3m = complaint.get("complaint_count_3m")
    if count_3m and int(count_3m) >= 2:
        ctype = complaint.get("complaint_type", "")
        reasons.append(f"近期投诉频繁({ctype})" if ctype else "近期投诉频繁")
    network = entities.get("NetworkQuality", {})
    speed = network.get("avg_download_speed")
    if speed and float(speed) < 50:
        reasons.append("网络体验差")
    competitor = entities.get("CompetitorActivity", {})
    if competitor.get("competitor_name") and competitor.get("competitor_name") != "-":
        reasons.append("竞品活动吸引")
    family = entities.get("FamilyGroup", {})
    ported = family.get("ported_member_count")
    if ported and int(ported) >= 1:
        reasons.append("家庭成员已携转")
    subscriber = entities.get("CbssSubscriber", {})
    innet = subscriber.get("innet_months")
    if innet and int(innet) < 12:
        reasons.append("在网时间短")
    if not reasons:
        reasons.append("无明显流失动因")
    return reasons


# PLACEHOLDER_RECOMMEND_ACTIONS


def _recommend_actions(db: Session, risk_level: str, reasons: list[str]) -> list[str]:
    from app.models.rule import EntityAction
    actions = []
    entity, _ = _get_entity_and_ds(db, "MnpRiskUser")
    if entity:
        db_actions = db.query(EntityAction).filter(
            EntityAction.entity_id == entity.id, EntityAction.status == "active"
        ).all()
        if db_actions:
            return [a.name for a in db_actions][:5]
    reason_action_map = {
        "合约即将到期": "发送专属优惠",
        "网络体验差": "网络质量优化",
        "竞品活动吸引": "套餐升级推荐",
        "家庭成员已携转": "一键外呼关怀",
        "近期投诉频繁": "一键外呼关怀",
        "在网时间短": "一键发送挽留短信",
    }
    for reason in reasons:
        for key, action in reason_action_map.items():
            if key in reason and action not in actions:
                actions.append(action)
    if risk_level == "high" and "一键外呼关怀" not in actions:
        actions.append("一键外呼关怀")
    if not actions:
        actions.append("一键发送挽留短信")
    return actions[:5]


@register_skill("mnp_risk_evaluate")
def mnp_risk_evaluate(params: dict, db: Session) -> dict:
    user_id = params.get("user_id", "")
    if not user_id:
        return {"success": False, "summary": "缺少 user_id 参数", "data": {}}

    subscriber_row = _query_user_row(db, "CbssSubscriber", user_id)
    device_number = str(subscriber_row.get("device_number", "")) if subscriber_row else ""

    entities_data: dict[str, dict] = {}
    for ename in _MNP_ENTITIES:
        row = _query_user_row(db, ename, user_id, device_number)
        if row:
            entities_data[ename] = {k: _serialize(v) for k, v in row.items()}

    if not entities_data:
        return {"success": False, "summary": f"未找到用户 {user_id} 的数据", "data": {}}

    evaluator = RuleEvaluator(db)
    try:
        eval_result = evaluator.evaluate_all(user_id)
    except Exception as e:
        eval_result = {"overall_risk": "none", "results": [], "triggered_count": 0, "evaluated_count": 0}

    _REVERSE_ALIAS = {v: k for k, v in _ENTITY_ALIAS.items()}
    rule_results = []
    for r in eval_result.get("results", []):
        conditions = []
        for c in r.get("conditions", []):
            field = c.get("field", "")
            parts = field.split(".", 1) if "." in field else [field, ""]
            db_entity = parts[0]
            frontend_entity = _REVERSE_ALIAS.get(db_entity, db_entity)
            conditions.append({
                "condition": c.get("display", field),
                "sourceEntity": frontend_entity,
                "sourceAttribute": parts[1] if len(parts) > 1 else "",
                "operator": c.get("operator", ""),
                "threshold": str(c.get("expected", "")),
                "actual": str(c.get("actual", "")),
                "matched": c.get("matched", False),
            })
        rule_results.append({
            "ruleName": r.get("rule_name", ""),
            "riskLevel": r.get("risk_level"),
            "triggered": r.get("triggered", False),
            "matchedCount": r.get("matched_count", 0),
            "totalCount": r.get("total_count", 0),
            "conditions": conditions,
        })

    risk_score = _calc_risk_score(eval_result)
    if risk_score >= 65:
        final_risk = "high"
    elif risk_score >= 40:
        final_risk = "medium"
    elif risk_score > 0:
        final_risk = "low"
    else:
        final_risk = "none"

    churn_reasons = _analyze_churn_reasons(entities_data)
    recommended_actions = _recommend_actions(db, final_risk, churn_reasons)
    channel_map = {"high": "专属坐席", "medium": "自动外呼", "low": "短信触达", "none": "短信触达"}

    data = {
        "user_id": user_id,
        "entities": entities_data,
        "ruleResults": rule_results,
        "finalRiskLevel": final_risk,
        "riskScore": risk_score,
        "churnReasonTop3": churn_reasons[:3],
        "recommendedActions": recommended_actions,
        "assignedChannel": channel_map.get(final_risk, "短信触达"),
    }
    summary = f"用户 {user_id} 风险等级: {final_risk}，评分: {risk_score}，触发 {len([r for r in rule_results if r['triggered']])} 条规则"
    return {"success": True, "summary": summary, "data": data}


# ── 宽带退单稽核 ──────────────────────────────────────


def _get_bb_ds(db: Session) -> DataSource | None:
    return db.query(DataSource).filter(
        DataSource.name == "bb_install_churn", DataSource.enabled == True
    ).first()


def _bb_query(ds: DataSource, sql: str, limit: int = 50) -> list[dict]:
    result = execute_readonly_sql(ds, sql, limit=limit)
    if result.get("error"):
        return []
    cols = result.get("columns", [])
    rows = []
    for row in result.get("rows", []):
        d = {}
        for i in range(len(cols)):
            v = row[i]
            d[cols[i]] = v.isoformat() if hasattr(v, 'isoformat') else (float(v) if hasattr(v, 'as_tuple') else v)
        rows.append(d)
    return rows


@register_skill("broadband_audit")
def broadband_audit(params: dict, db: Session) -> dict:
    churn_id = params.get("churn_id", "")
    if not churn_id:
        return {"success": False, "summary": "缺少 churn_id 参数", "data": {}}

    ds = _get_bb_ds(db)
    if not ds:
        import pymysql
        try:
            conn = pymysql.connect(
                host="123.56.188.16", port=3306, user="bonc", password="bonc123",
                database="mnp_risk_warning", charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        except Exception as e:
            return {"success": False, "summary": f"无法连接宽带稽核数据库: {e}", "data": {}}
        try:
            return _broadband_audit_via_conn(conn, churn_id)
        finally:
            conn.close()

    churn_rows = _bb_query(ds, f"""
        SELECT c.*, o.product_name, o.biz_type, o.install_address,
               o.cust_id, o.engineer_id
        FROM bb_install_churn c
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        WHERE c.churn_id = '{churn_id}'
    """, 1)
    if not churn_rows:
        return {"success": False, "summary": f"退单 {churn_id} 不存在", "data": {}}

    churn = churn_rows[0]
    evidences = _bb_query(ds, f"""
        SELECT evidence_id, evidence_code, evidence_type, source_type,
               content, hit, confidence
        FROM bb_evidence WHERE churn_id = '{churn_id}'
        ORDER BY hit DESC, confidence DESC
    """, 100)

    root_causes = _bb_query(ds, f"""
        SELECT cause_category, cause_subcategory, confidence, evidence_chain
        FROM bb_root_cause WHERE churn_id = '{churn_id}'
        ORDER BY confidence DESC
    """, 10)

    data = {
        "churn_id": churn_id,
        "churn": churn,
        "evidences": evidences,
        "root_causes": root_causes,
        "audit_status": churn.get("audit_status", ""),
        "root_cause_level_one": churn.get("root_cause_level_one", ""),
        "root_cause_confidence": churn.get("root_cause_confidence", 0),
    }
    hit_count = len([e for e in evidences if e.get("hit")])
    summary = (
        f"退单 {churn_id}: 根因={churn.get('root_cause_level_one', '未知')}，"
        f"置信度={churn.get('root_cause_confidence', 0)}，"
        f"命中证据 {hit_count}/{len(evidences)} 条"
    )
    return {"success": True, "summary": summary, "data": data}


def _broadband_audit_via_conn(conn, churn_id: str) -> dict:
    """通过直连 pymysql 执行宽带稽核"""
    from datetime import date, datetime as dt
    from decimal import Decimal

    def ser(row: dict) -> dict:
        out = {}
        for k, v in row.items():
            if isinstance(v, (date, dt)):
                out[k] = v.isoformat()
            elif isinstance(v, Decimal):
                out[k] = float(v)
            else:
                out[k] = v
        return out

    def q(sql):
        with conn.cursor() as cur:
            cur.execute(sql)
            return [ser(r) for r in cur.fetchall()]

    churn = q(f"""
        SELECT c.*, o.product_name, o.biz_type, o.install_address,
               o.cust_id, o.engineer_id
        FROM bb_install_churn c
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        WHERE c.churn_id = '{churn_id}'
    """)
    if not churn:
        return {"success": False, "summary": f"退单 {churn_id} 不存在", "data": {}}

    evidences = q(f"""
        SELECT evidence_id, evidence_code, evidence_type, source_type,
               content, hit, confidence
        FROM bb_evidence WHERE churn_id = '{churn_id}'
        ORDER BY hit DESC, confidence DESC
    """)

    root_causes = q(f"""
        SELECT cause_category, cause_subcategory, confidence, evidence_chain
        FROM bb_root_cause WHERE churn_id = '{churn_id}'
        ORDER BY confidence DESC
    """)

    data = {
        "churn_id": churn_id,
        "churn": churn[0],
        "evidences": evidences,
        "root_causes": root_causes,
        "audit_status": churn[0].get("audit_status", ""),
        "root_cause_level_one": churn[0].get("root_cause_level_one", ""),
        "root_cause_confidence": churn[0].get("root_cause_confidence", 0),
    }
    hit_count = len([e for e in evidences if e.get("hit")])
    summary = (
        f"退单 {churn_id}: 根因={churn[0].get('root_cause_level_one', '未知')}，"
        f"置信度={churn[0].get('root_cause_confidence', 0)}，"
        f"命中证据 {hit_count}/{len(evidences)} 条"
    )
    return {"success": True, "summary": summary, "data": data}
