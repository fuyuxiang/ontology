"""
宽带装机退单稽核 — SSE 实时分析
"""
import hashlib
import json
import logging
import time
import uuid
from typing import Any

from .db import _execute, _insert_trail, _query, _query_one, _ser

logger = logging.getLogger(__name__)


def _sse_event(step: str, status: str, message: str = "", data: Any = None) -> str:
    import json as _json
    payload = {"step": step, "status": status, "message": message}
    if data is not None:
        payload["data"] = data
    return f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"


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

    _execute("DELETE FROM bb_audit_action WHERE churn_id=%s", (churn_id,))

    evidence_raw = _query("SELECT * FROM bb_evidence WHERE churn_id=%s", (churn_id,))
    todos = _make_todos(churn_id, churn, [_ser(e) for e in evidence_raw],
                        root_cause_l1, order, customer, address)

    for todo in todos:
        params_val = json.dumps(todo.get("params_json"), ensure_ascii=False) if todo.get("params_json") else None
        inserted = False
        try:
            _execute(
                "INSERT INTO bb_audit_action "
                "(action_id, churn_id, action_type_code, todo_type, action_name, description, "
                "priority, status, assignee, params_json, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())",
                (todo["action_id"], churn_id, todo["action_type_code"],
                 todo.get("todo_type", todo["action_type_code"]),
                 todo["action_name"], todo["description"],
                 todo["priority"], todo["status"], todo.get("assignee"), params_val)
            )
            inserted = True
        except Exception:
            try:
                _execute(
                    "INSERT INTO bb_audit_action "
                    "(action_id, churn_id, action_type_code, action_name, description, "
                    "priority, status, assignee, params_json, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())",
                    (todo["action_id"], churn_id, todo["action_type_code"],
                     todo["action_name"], todo["description"],
                     todo["priority"], todo["status"], todo.get("assignee"), params_val)
                )
                inserted = True
            except Exception as e2:
                logger.exception("插入推荐动作失败 churn_id=%s action_id=%s: %s", churn_id, todo["action_id"], e2)
                yield _sse_event("todo", "error", f"动作写入失败：{todo['action_name']}", {"error": str(e2)})
                continue
        if inserted:
            _insert_trail(churn_id, "action_created",
                          f"生成推荐动作 {todo['action_name']}（{todo['priority']}）", "system")
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

