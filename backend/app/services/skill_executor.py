"""
内置 Skill 执行器 — 将场景验证的业务逻辑封装为可复用的 skill 函数
每个 skill 函数签名: (params: dict, db: Session) -> dict
返回统一格式: { success: bool, summary: str, data: dict }
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import OntologyEntity, BusinessRule
from app.services.data_plane.entity_data_service import EntityDataService
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
    if fn:
        try:
            return fn(params, db)
        except Exception as e:
            logger.error(f"Skill {code_ref} 执行失败: {e}")
            return {"success": False, "summary": f"执行失败: {e}", "data": {}}
    # Fallback: check for generated skill
    from app.models.skill import Skill
    skill = db.query(Skill).filter(Skill.code_ref == code_ref, Skill.skill_type == "generated", Skill.status == "active").first()
    if skill:
        return execute_generated_skill(skill, params, db)
    return {"success": False, "summary": f"未知 skill: {code_ref}", "data": {}}


SKILL_STREAM_REGISTRY: dict[str, callable] = {}


def register_skill_stream(code_ref: str):
    def decorator(fn):
        SKILL_STREAM_REGISTRY[code_ref] = fn
        return fn
    return decorator


def has_skill_stream(code_ref: str) -> bool:
    return code_ref in SKILL_STREAM_REGISTRY


def execute_skill_stream(code_ref: str, params: dict, db: Session):
    fn = SKILL_STREAM_REGISTRY.get(code_ref)
    if not fn:
        result = execute_skill(code_ref, params, db)
        yield {"step": "result", "status": "complete", "summary": result.get("summary", ""), "data": result.get("data", {})}
        return
    try:
        yield from fn(params, db)
    except Exception as e:
        logger.error(f"Skill stream {code_ref} 执行失败: {e}")
        yield {"step": "error", "status": "error", "message": str(e)}


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


def _get_entity_and_asset(db: Session, entity_name: str):
    db_name = _ENTITY_ALIAS.get(entity_name, entity_name)
    entity = db.query(OntologyEntity).filter(OntologyEntity.id == f"{_NS}_{db_name}").first()
    if not entity:
        entity = db.query(OntologyEntity).filter(OntologyEntity.name == db_name).first()
    if not entity:
        entity = db.query(OntologyEntity).filter(OntologyEntity.id == f"{_NS}_{entity_name}").first()
    if not entity:
        return None, None
    svc = EntityDataService(db)
    resolved = svc.resolve_entity_asset(entity.id)
    if not resolved:
        return entity, None
    asset, _ = resolved
    return entity, asset


def _query_user_row(db: Session, entity_name: str, user_id: str, device_number: str = "") -> dict:
    entity, asset = _get_entity_and_asset(db, entity_name)
    if not entity or not asset:
        return {}
    svc = EntityDataService(db)
    table_name = svc.get_table_name(asset)
    if not table_name:
        return {}
    pk_field = (entity.schema_json or {}).get("primary_key", "user_id")
    if pk_field in ("sheet_id",) and device_number:
        where_col, where_val = "device_number", device_number
    elif pk_field == "device_number" and device_number:
        where_col, where_val = "device_number", device_number
    elif pk_field == "subs_id":
        where_col, where_val = "subs_id", user_id
    else:
        where_col, where_val = pk_field, user_id
    sql = f"SELECT * FROM {table_name} WHERE {where_col} = :pk_val LIMIT 1"
    result = svc.execute_sql_on_entity(
        entity.id, sql, params={"pk_val": where_val}, purpose="skill.query_user_row",
    )
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
    entity, _ = _get_entity_and_asset(db, "MnpRiskUser")
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


_BB_CONN_NAME = "bb_audit_db"


def _bb_query_named(
    db: Session, sql: str, params: dict, *, purpose: str, limit: int = 50,
) -> list[dict]:
    """通过 Data Plane 跑参数化 SQL，返回 list[dict]。

    走 ExecuteService.execute_on_connection（统一闸口：AST 校验 / 限流 / 审计 / 脱敏）。
    Connection 必须由用户在「数据接入·连接」页提前创建（默认名：bb_audit_db）。
    """
    from datetime import date as _date, datetime as _dt
    from decimal import Decimal
    from app.repositories.connection_repo import ConnectionRepository
    from app.services.data_plane.execute_service import (
        ExecuteBlocked, ExecuteService,
    )

    conn = ConnectionRepository(db).find_by_name(_BB_CONN_NAME)
    if not conn:
        logger.warning("业务连接「%s」未就绪，跳过查询", _BB_CONN_NAME)
        return []
    try:
        r = ExecuteService(db).execute_on_connection(
            connection_id=conn.id,
            sql=sql, params=params, purpose=purpose, write=False,
        )
    except ExecuteBlocked as e:
        logger.warning("broadband SQL 被拒绝: %s %s", e.reason, e.detail)
        return []
    except Exception as e:
        logger.warning("broadband SQL 执行失败: %s", e)
        return []

    cols = r.columns
    out: list[dict] = []
    for row in r.rows[:limit]:
        d: dict = {}
        for i, c in enumerate(cols):
            v = row[i]
            if isinstance(v, (_date, _dt)):
                d[c] = v.isoformat()
            elif isinstance(v, Decimal):
                d[c] = float(v)
            else:
                d[c] = v
        out.append(d)
    return out


@register_skill("broadband_audit")
def broadband_audit(params: dict, db: Session) -> dict:
    churn_id = params.get("churn_id", "")
    if not churn_id:
        return {"success": False, "summary": "缺少 churn_id 参数", "data": {}}

    churn_rows = _bb_query_named(db, """
        SELECT c.*, o.product_name, o.biz_type, o.install_address,
               o.cust_id, o.engineer_id
        FROM bb_install_churn c
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        WHERE c.churn_id = :churn_id
    """, {"churn_id": churn_id}, purpose="skill.broadband_audit.churn", limit=1)
    if not churn_rows:
        return {"success": False, "summary": f"退单 {churn_id} 不存在", "data": {}}

    churn = churn_rows[0]
    evidences = _bb_query_named(db, """
        SELECT evidence_id, evidence_code, evidence_type, source_type,
               content, hit, confidence
        FROM bb_evidence WHERE churn_id = :churn_id
        ORDER BY hit DESC, confidence DESC
    """, {"churn_id": churn_id}, purpose="skill.broadband_audit.evidence", limit=100)

    root_causes = _bb_query_named(db, """
        SELECT cause_category, cause_subcategory, confidence, evidence_chain
        FROM bb_root_cause WHERE churn_id = :churn_id
        ORDER BY confidence DESC
    """, {"churn_id": churn_id}, purpose="skill.broadband_audit.root_cause", limit=10)

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


@register_skill_stream("broadband_audit")
def broadband_audit_stream(params: dict, db: Session):
    """流式版宽带退单稽核 — yield 5 步分析事件，与场景验证 _analysis_stream 对齐。

    全部 SQL 走 ExecuteService.execute_on_connection（参数化 + 审计）。
    """
    churn_id = params.get("churn_id", "")
    if not churn_id:
        yield {"step": "error", "status": "error", "message": "缺少 churn_id 参数"}
        return

    from app.repositories.connection_repo import ConnectionRepository
    if not ConnectionRepository(db).find_by_name(_BB_CONN_NAME):
        yield {
            "step": "error", "status": "error",
            "message": f"业务连接「{_BB_CONN_NAME}」未就绪，请在「数据接入·连接」页创建",
        }
        return

    def q(sql: str, p: dict, purpose: str = "skill.broadband_audit_stream") -> list[dict]:
        return _bb_query_named(db, sql, p, purpose=purpose, limit=1000)

    # Step 1: 感知 · 数据采集
    churn_rows = q(
        """
        SELECT c.*, o.product_name, o.biz_type, o.install_address,
               o.cust_id, o.engineer_id
        FROM bb_install_churn c
        LEFT JOIN bb_install_order o ON c.related_order_no = o.order_no
        WHERE c.churn_id = :churn_id
        """,
        {"churn_id": churn_id}, "skill.broadband_audit_stream.churn",
    )
    if not churn_rows:
        yield {"step": "error", "status": "error", "message": f"退单 {churn_id} 不存在"}
        return
    churn = churn_rows[0]
    order_no = churn.get("related_order_no", "") or ""
    cust_id = churn.get("cust_id", "") or ""
    engineer_id = churn.get("engineer_id", "") or ""

    source_types: dict[str, int] = {}
    if order_no and q(
        "SELECT 1 AS x FROM bb_install_order WHERE order_no = :order_no LIMIT 1",
        {"order_no": order_no}, "skill.bb.src.order",
    ):
        source_types["工单"] = 1
    if cust_id and q(
        "SELECT 1 AS x FROM bb_customer WHERE customer_id = :cust_id LIMIT 1",
        {"cust_id": cust_id}, "skill.bb.src.customer",
    ):
        source_types["客户"] = 1
    if engineer_id and q(
        "SELECT 1 AS x FROM bb_engineer WHERE engineer_id = :engineer_id LIMIT 1",
        {"engineer_id": engineer_id}, "skill.bb.src.engineer",
    ):
        source_types["工程师"] = 1

    eng_calls = q(
        "SELECT call_id FROM bb_engineer_call WHERE related_order_no = :order_no",
        {"order_no": order_no}, "skill.bb.calls.engineer",
    ) if order_no else []
    cb_calls = q(
        "SELECT call_id FROM bb_callback_call WHERE related_order_no = :order_no",
        {"order_no": order_no}, "skill.bb.calls.callback",
    ) if order_no else []
    comp_calls = q(
        "SELECT call_id FROM bb_competitor_call WHERE customer_id = :cust_id",
        {"cust_id": cust_id}, "skill.bb.calls.competitor",
    ) if cust_id else []
    if eng_calls:
        source_types["工程师通话"] = len(eng_calls)
    if cb_calls:
        source_types["回访通话"] = len(cb_calls)
    if comp_calls:
        source_types["异网通话"] = len(comp_calls)

    yield {
        "step": "perception", "status": "complete",
        "label": "感知·数据采集",
        "summary": f"采集完成，共 {sum(source_types.values())} 条数据源",
        "data": {"type": "broadband_perception", "source_types": source_types,
                 "total_sources": sum(source_types.values())},
    }

    # Step 2: 识别 · 证据提取
    evidence = q(
        "SELECT * FROM bb_evidence WHERE churn_id = :churn_id",
        {"churn_id": churn_id}, "skill.bb.evidence",
    )
    nlp_ev = [e for e in evidence if e.get("evidence_type") == "nlp"]
    rule_ev = [e for e in evidence if e.get("evidence_type") == "rule"]
    hit_count = sum(1 for e in evidence if e.get("hit"))

    yield {
        "step": "recognition", "status": "complete",
        "label": "识别·证据提取",
        "summary": f"NLP证据 {len(nlp_ev)} 条，规则证据 {len(rule_ev)} 条，命中 {hit_count} 条",
        "data": {"type": "broadband_recognition", "nlp_count": len(nlp_ev),
                 "rule_count": len(rule_ev), "hit_count": hit_count, "total": len(evidence),
                 "hit_codes": [e.get("evidence_code") for e in evidence if e.get("hit")]},
    }

    # Step 3: 推理 · 逻辑命中
    logic_hits = q(
        "SELECT * FROM bb_logic_hit WHERE churn_id = :churn_id ORDER BY executed_at",
        {"churn_id": churn_id}, "skill.bb.logic_hit",
    )
    lf_names = list({lh.get("logic_function_name", lh.get("logic_function_id", "")) for lh in logic_hits})

    yield {
        "step": "reasoning", "status": "complete",
        "label": "推理·逻辑命中",
        "summary": f"逻辑推理完成，命中 {len(logic_hits)} 条规则",
        "data": {"type": "broadband_reasoning", "hit_count": len(logic_hits),
                 "logic_functions": lf_names[:10]},
    }

    # Step 4: 归因 · 结论输出
    root_cause_l1 = churn.get("root_cause_level_one", "") or ""
    root_cause_l2 = churn.get("root_cause_level_two", "") or ""
    confidence = float(churn["root_cause_confidence"]) if churn.get("root_cause_confidence") else 0.0

    yield {
        "step": "attribution", "status": "complete",
        "label": "归因·结论输出",
        "summary": f"根因: {root_cause_l1 or '未知'} / {root_cause_l2 or '-'}，置信度: {confidence*100:.1f}%",
        "data": {"type": "broadband_attribution",
                 "root_cause_level_one": root_cause_l1, "root_cause_level_two": root_cause_l2,
                 "confidence": confidence, "audit_status": churn.get("audit_status", "")},
    }

    # Step 5: 动作 · 推荐生成
    actions = q(
        "SELECT action_name, priority, status FROM bb_audit_action "
        "WHERE churn_id = :churn_id ORDER BY created_at",
        {"churn_id": churn_id}, "skill.bb.actions",
    )

    yield {
        "step": "todo", "status": "complete",
        "label": "动作·推荐生成",
        "summary": f"共 {len(actions)} 个推荐动作" if actions else "无需生成动作",
        "data": {"type": "broadband_todo", "action_count": len(actions),
                 "actions": [a.get("action_name", "") for a in actions[:5]]},
    }

    # Final result
    yield {
        "step": "result", "status": "complete",
        "summary": (
            f"退单 {churn_id}: 根因={root_cause_l1 or '未知'}，"
            f"置信度={confidence:.2f}，命中证据 {hit_count}/{len(evidence)} 条"
        ),
        "data": {
            "churn_id": churn_id, "churn": churn, "evidences": evidence,
            "audit_status": churn.get("audit_status", ""),
            "root_cause_level_one": root_cause_l1, "root_cause_confidence": confidence,
        },
    }


def execute_skill_tool_call(tool_type: str, tool_config: dict, params: dict, db: Session) -> dict:
    """Execute a rule or function tool referenced by a skill."""
    if tool_type == "rule":
        rule_id = tool_config.get("rule_id")
        if not rule_id:
            return {"success": False, "summary": "Missing rule_id", "data": {}}
        rule = db.query(BusinessRule).get(rule_id)
        if not rule:
            return {"success": False, "summary": f"Rule {rule_id} not found", "data": {}}
        user_id = params.get("user_id", "")
        evaluator = RuleEvaluator(db)
        result = evaluator.evaluate(rule, user_id)
        db.commit()
        return {
            "success": True,
            "summary": f"Rule '{result.rule_name}' {'triggered' if result.triggered else 'not triggered'}",
            "data": {
                "triggered": result.triggered,
                "confidence": result.confidence,
                "risk_level": result.risk_level,
                "matched_count": result.matched_count,
                "total_count": result.total_count,
            },
        }

    elif tool_type == "function":
        from app.services.function_executor import FunctionExecutor
        callable_name = tool_config.get("callable_name")
        func_id = tool_config.get("function_id")
        executor = FunctionExecutor(db)
        if callable_name:
            result = executor.execute_by_callable_name(callable_name, params)
        elif func_id:
            from app.models.function import OntologyFunction
            func = db.get(OntologyFunction, func_id)
            if not func:
                return {"success": False, "summary": f"Function {func_id} not found", "data": {}}
            result = executor.execute(func, params)
        else:
            return {"success": False, "summary": "Missing callable_name or function_id", "data": {}}

        return {
            "success": result.success,
            "summary": f"Function returned: {result.value}" if result.success else f"Error: {result.error}",
            "data": {"value": result.value, "execution_ms": result.execution_ms},
        }

    return {"success": False, "summary": f"Unknown tool type: {tool_type}", "data": {}}


def execute_generated_skill(skill, params: dict, db) -> dict:
    """Execute a generated skill by running its tools in sandbox."""
    from app.models.skill_tool import SkillTool
    from app.services.skill_sandbox import execute_in_sandbox

    tools = db.query(SkillTool).filter(SkillTool.skill_id == skill.id).all()
    results = {}
    for tool in tools:
        try:
            output = execute_in_sandbox(tool.code, tool.name, params)
            results[tool.name] = {"success": True, "output": output}
        except Exception as e:
            results[tool.name] = {"success": False, "error": str(e)}

    return {
        "success": all(r["success"] for r in results.values()),
        "summary": f"Executed {len(tools)} tools",
        "data": results,
    }
