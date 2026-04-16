"""
场景 API — 携号转网预警全流程编排
复用本体数据源查询和规则引擎，为前端提供真实实例数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any

from app.database import get_db
from app.models import OntologyEntity, DataSource, BusinessRule, EntityAction
from app.services.datasource_utils import execute_readonly_sql
from app.services.rule_engine import RuleEvaluator

router = APIRouter(prefix="/scenes", tags=["scenes"])


# ── 响应模型 ──────────────────────────────────────────

class MnpUserBrief(BaseModel):
    user_id: str
    name: str | None = None
    phone: str | None = None
    innet_months: int | None = None
    is_5g: bool | None = None
    pay_mode: str | None = None

class EntityInstanceData(BaseModel):
    entity_name: str
    entity_name_cn: str
    data: dict[str, Any]

class RuleConditionResult(BaseModel):
    condition: str
    sourceEntity: str
    sourceAttribute: str
    operator: str
    threshold: str
    actual: str
    matched: bool

class RuleEvalResult(BaseModel):
    ruleName: str
    riskLevel: str | None = None
    triggered: bool
    matchedCount: int
    totalCount: int
    conditions: list[RuleConditionResult]

class MnpExecuteResult(BaseModel):
    user_id: str
    entities: dict[str, dict[str, Any]]
    ruleResults: list[RuleEvalResult]
    finalRiskLevel: str
    riskScore: int
    churnReasonTop3: list[str]
    recommendedActions: list[str]
    assignedChannel: str


# ── 场景实体映射 ──────────────────────────────────────

# s5 命名空间下的实体名 → 实体 ID 前缀
_NS = "s5"

# 前端实体名 → 数据库实际实体名的映射
_ENTITY_ALIAS: dict[str, str] = {
    "CbssSubscriber": "MobileSubscriber",
    "MnpEligibilityQuery": "PortabilityQuery",
    "SubscriberContract": "UserContract",
    "CustomerComplaint": "ComplaintWorkOrder",
    "NetworkQuality": "MonthlyBilling",
    "CompetitorActivity": "VoiceCallRecord",
    "FamilyGroup": "ConvergencePackage",
    "MnpRiskUser": "RetentionRecord",
}

# 需要查询的实体列表（前端名称）
_MNP_ENTITIES = list(_ENTITY_ALIAS.keys())


def _get_entity_and_ds(db: Session, entity_name: str) -> tuple[OntologyEntity | None, DataSource | None]:
    """通过实体名查找本体实体和关联数据源，支持别名映射"""
    # 先通过别名映射到数据库实际名称
    db_name = _ENTITY_ALIAS.get(entity_name, entity_name)

    # 尝试带命名空间前缀
    entity = db.query(OntologyEntity).filter(OntologyEntity.id == f"{_NS}_{db_name}").first()
    if not entity:
        entity = db.query(OntologyEntity).filter(OntologyEntity.name == db_name).first()
    if not entity:
        # 再试原始名称
        entity = db.query(OntologyEntity).filter(OntologyEntity.id == f"{_NS}_{entity_name}").first()
    if not entity:
        return None, None

    ds_ref = (entity.schema_json or {}).get("datasource_ref", "")
    if not ds_ref:
        return entity, None

    ds = db.query(DataSource).filter(DataSource.name == ds_ref, DataSource.enabled == True).first()
    return entity, ds


def _query_user_row(db: Session, entity_name: str, user_id: str, device_number: str = "") -> dict[str, Any]:
    """查询某实体下指定用户的一行数据，支持按 user_id 或 device_number 关联"""
    entity, ds = _get_entity_and_ds(db, entity_name)
    if not entity or not ds or not ds.table_name:
        return {}

    pk_field = (entity.schema_json or {}).get("primary_key", "user_id")

    # 根据主键类型选择关联字段和值
    if pk_field in ("sheet_id",) and device_number:
        where = f"device_number = '{device_number}'"
    elif pk_field == "device_number" and device_number:
        where = f"device_number = '{device_number}'"
    elif pk_field == "subs_id":
        where = f"subs_id = '{user_id}'"
    else:
        where = f"{pk_field} = '{user_id}'"

    # 用 SELECT * 避免列名不匹配问题
    sql = f"SELECT * FROM {ds.table_name} WHERE {where} LIMIT 1"
    result = execute_readonly_sql(ds, sql, limit=1)
    if result.get("error") or not result.get("rows"):
        return {}

    columns = result["columns"]
    row = result["rows"][0]
    return {columns[i]: row[i] for i in range(len(columns))}


# ── 接口 1: 获取候选用户列表 ──────────────────────────

@router.get("/mnp/users", response_model=list[MnpUserBrief])
def list_mnp_users(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """从 CbssSubscriber 数据源获取候选用户列表"""
    entity, ds = _get_entity_and_ds(db, "CbssSubscriber")
    if not entity or not ds or not ds.table_name:
        raise HTTPException(status_code=404, detail="CbssSubscriber 实体未关联可用数据源")

    pk_field = (entity.schema_json or {}).get("primary_key", "user_id")
    sql = f"SELECT * FROM {ds.table_name} LIMIT {limit}"
    result = execute_readonly_sql(ds, sql, limit=limit)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    users = []
    columns = result.get("columns", [])
    for row in result.get("rows", []):
        row_dict = {columns[i]: row[i] for i in range(len(columns))}
        phone = str(row_dict.get("device_number", ""))
        if len(phone) >= 7:
            phone = phone[:3] + "****" + phone[-4:]
        users.append(MnpUserBrief(
            user_id=str(row_dict.get(pk_field, "")),
            phone=phone,
            innet_months=row_dict.get("innet_months"),
            is_5g=row_dict.get("is_5g") in (True, 1, "是", "true", "1"),
            pay_mode=str(row_dict.get("pay_mode", "")),
        ))
    return users


# ── 接口 1.5: 获取按风险分布筛选的案例用户 ──────────────

class MnpCaseUser(BaseModel):
    user_id: str
    name: str | None = None
    phone: str | None = None
    innet_months: int | None = None
    is_5g: bool | None = None
    pay_mode: str | None = None
    finalRiskLevel: str = "none"
    riskScore: int = 0


# ── 案例用户缓存 ──────────────────────────────────────
_case_users_cache: list["MnpCaseUser"] | None = None
_execute_cache: dict[str, dict] = {}


@router.get("/mnp/case-users", response_model=list[MnpCaseUser])
def list_mnp_case_users(db: Session = Depends(get_db)):
    """
    获取案例用户列表：首次调用时评估并缓存，后续直接返回缓存结果。
    """
    global _case_users_cache
    if _case_users_cache is not None:
        return _case_users_cache
    # 1. 拉取足够多的候选用户
    entity, ds = _get_entity_and_ds(db, "CbssSubscriber")
    if not entity or not ds or not ds.table_name:
        raise HTTPException(status_code=404, detail="CbssSubscriber 实体未关联可用数据源")

    pk_field = (entity.schema_json or {}).get("primary_key", "user_id")
    sql = f"SELECT * FROM {ds.table_name} LIMIT 50"
    result = execute_readonly_sql(ds, sql, limit=50)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    columns = result.get("columns", [])
    rows = result.get("rows", [])

    # 2. 对每个用户执行规则评估，收集分数
    evaluator = RuleEvaluator(db)
    all_users: list[MnpCaseUser] = []

    for row in rows:
        row_dict = {columns[i]: row[i] for i in range(len(columns))}
        uid = str(row_dict.get(pk_field, ""))
        if not uid:
            continue

        phone = str(row_dict.get("device_number", ""))
        if len(phone) >= 7:
            phone = phone[:3] + "****" + phone[-4:]

        # 评估风险
        try:
            eval_result = evaluator.evaluate_all(uid)
        except Exception:
            eval_result = {"overall_risk": "none", "results": []}

        risk_score = _calc_risk_score(eval_result)

        user = MnpCaseUser(
            user_id=uid,
            name=row_dict.get("name") or uid,
            phone=phone,
            innet_months=row_dict.get("innet_months"),
            is_5g=row_dict.get("is_5g") in (True, 1, "是", "true", "1"),
            pay_mode=str(row_dict.get("pay_mode", "")),
            finalRiskLevel="none",
            riskScore=risk_score,
        )
        all_users.append(user)

    # 3. 按分数降序排列，用相对排名分配风险等级
    #    分数区间：>=65 高风险, 40-64 中风险, <40 低风险
    all_users.sort(key=lambda u: -u.riskScore)
    for u in all_users:
        if u.riskScore >= 65:
            u.finalRiskLevel = "high"
        elif u.riskScore >= 40:
            u.finalRiskLevel = "medium"
        else:
            u.finalRiskLevel = "low"

    # 4. 按 1高 / 3中 / 2低 选取
    buckets: dict[str, list[MnpCaseUser]] = {"high": [], "medium": [], "low": []}
    for u in all_users:
        buckets.setdefault(u.finalRiskLevel, []).append(u)

    quota = {"high": 1, "medium": 3, "low": 2}
    selected: list[MnpCaseUser] = []

    for level, count in quota.items():
        pool = buckets.get(level, [])
        selected.extend(pool[:count])

    # 如果某个桶不够，从其他桶补齐到 6 个
    if len(selected) < 6:
        used_ids = {u.user_id for u in selected}
        for u in all_users:
            if u.user_id not in used_ids:
                selected.append(u)
                used_ids.add(u.user_id)
                if len(selected) >= 6:
                    break

    # 按风险分数降序排列（高风险在前）
    risk_order = {"high": 0, "medium": 1, "low": 2, "none": 3}
    selected.sort(key=lambda u: (risk_order.get(u.finalRiskLevel, 3), -u.riskScore))

    _case_users_cache = selected[:6]
    return _case_users_cache


# ── 接口 2: 执行全流程编排 ──────────────────────────

@router.get("/mnp/execute")
def execute_mnp_flow(
    user_id: str = Query(..., description="用户标识"),
    db: Session = Depends(get_db),
):
    """对指定用户执行携号转网全流程编排，返回每个实体的实例数据和规则评估结果"""

    if user_id in _execute_cache:
        return _execute_cache[user_id]

    # 0. 先查 MobileSubscriber 获取 device_number，用于关联其他表
    subscriber_row = _query_user_row(db, "CbssSubscriber", user_id)
    device_number = str(subscriber_row.get("device_number", "")) if subscriber_row else ""

    # 1. 拉取所有实体的实例数据
    entities_data: dict[str, dict[str, Any]] = {}
    for ename in _MNP_ENTITIES:
        row = _query_user_row(db, ename, user_id, device_number)
        if row:
            entities_data[ename] = {k: _serialize(v) for k, v in row.items()}

    if not entities_data:
        raise HTTPException(status_code=404, detail=f"未找到用户 {user_id} 的实例数据")

    # 2. 评估所有规则（容错处理）
    rule_results: list[dict] = []
    eval_result: dict = {"overall_risk": "none", "results": []}
    try:
        evaluator = RuleEvaluator(db)
        eval_result = evaluator.evaluate_all(user_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"规则评估失败: {e}")
    # 数据库实体名 → 前端实体名的反向映射
    _REVERSE_ALIAS = {v: k for k, v in _ENTITY_ALIAS.items()}

    for r in eval_result.get("results", []):
        conditions = []
        for c in r.get("conditions", []):
            # 从 field 中解析 sourceEntity 和 sourceAttribute
            field = c.get("field", "")
            parts = field.split(".", 1) if "." in field else [field, ""]
            db_entity = parts[0]
            # 映射回前端名称
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

    final_risk = eval_result.get("overall_risk", "none")
    risk_score = _calc_risk_score(eval_result)

    # 用分数区间重新定级，保证与 case-users 接口一致
    if risk_score >= 65:
        final_risk = "high"
    elif risk_score >= 40:
        final_risk = "medium"
    elif risk_score > 0:
        final_risk = "low"

    # 3. 根因分析（基于实例数据推断）
    churn_reasons = _analyze_churn_reasons(entities_data)

    # 4. 推荐动作（基于规则和实体数据）
    recommended_actions = _recommend_actions(db, final_risk, churn_reasons)

    # 5. 分发渠道
    channel_map = {"high": "专属坐席", "medium": "自动外呼", "low": "短信触达", "none": "短信触达"}
    assigned_channel = channel_map.get(final_risk, "短信触达")

    result = {
        "user_id": user_id,
        "entities": entities_data,
        "ruleResults": rule_results,
        "finalRiskLevel": final_risk,
        "riskScore": risk_score,
        "churnReasonTop3": churn_reasons[:3],
        "recommendedActions": recommended_actions,
        "assignedChannel": assigned_channel,
    }
    _execute_cache[user_id] = result
    return result


# ── 辅助函数 ──────────────────────────────────────────

def _serialize(val: Any) -> Any:
    """将数据库值转为 JSON 可序列化格式"""
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
    """根据规则评估结果计算风险评分"""
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


def _analyze_churn_reasons(entities: dict[str, dict[str, Any]]) -> list[str]:
    """基于实例数据推断流失根因"""
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


def _recommend_actions(db: Session, risk_level: str, reasons: list[str]) -> list[str]:
    """基于风险等级和根因推荐维系动作"""
    actions = []

    # 尝试从数据库中获取已定义的动作
    entity, _ = _get_entity_and_ds(db, "MnpRiskUser")
    if entity:
        db_actions = db.query(EntityAction).filter(
            EntityAction.entity_id == entity.id,
            EntityAction.status == "active",
        ).all()
        if db_actions:
            for a in db_actions:
                actions.append(a.name)
            return actions[:5]

    # 兜底：基于规则推荐
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
