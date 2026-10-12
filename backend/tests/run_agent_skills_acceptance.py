"""Fresh HTTP acceptance; create/test/publish Skills and Agents using real routes.

Requires a published ontology created by the UI/API acceptance flow, a deterministic
Function and a published Action. No business release state is written into the DB.
External LLM provider may be the local controlled OpenAI protocol from run_review_server.
"""
import argparse
import json
import os
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:5055")
    parser.add_argument("--ontology-id", required=True)
    parser.add_argument("--version-id", required=True)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--function-id", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--action-params", default='{"device_id":"DEV-001","reason":"温度过高"}')
    parser.add_argument("--receipt-url", default="http://127.0.0.1:5056/fixture/state",
                        help="Isolated receipt service GET; leave empty for a different business source")
    parser.add_argument("--output", default="../docs/review/evidence/agd-skills-agent-fresh.json")
    args = parser.parse_args()
    assert args.api.startswith("http://127.0.0.1:"), "This acceptance script only writes to an isolated loopback server"
    client = httpx.Client(base_url=args.api, timeout=120, trust_env=False)
    records = []
    def call(method, path, payload=None, headers=None, expected=200):
        response = client.request(method, "/api/v1" + path, json=payload, headers=headers)
        value = response.json() if response.content else None
        assert response.status_code == expected, (method, path, response.status_code, value)
        if not path.startswith("/auth"):
            records.append({"method": method, "path": path, "status": response.status_code,
                            "result": {k: v for k, v in value.items() if k not in {"api_key", "curl"}} if isinstance(value, dict) else value})
        return value
    login = call("POST", "/auth/login", {"username": os.environ.get("REVIEW_USERNAME", "admin"),
        "password": os.environ["REVIEW_PASSWORD"]})
    client.headers["Authorization"] = "Bearer " + login["token"]
    cfg = {"ontology_id": args.ontology_id, "ontology_version_id": args.version_id,
           "action_mode": "simulation", "max_tool_rounds": 12}
    skill = call("POST", "/skills", {"name": "验收设备处置技能", "visibility": "workspace",
        "ontology_id": args.ontology_id, "ontology_version_id": args.version_id, "entity_ids": [args.entity_id],
        "description": "真实工具返回决定执行结果", "prompt_template": "先加载技能，计算确定性设备风险，模拟检修工单处置；请报告风险和确认要求。",
        "tools": [{"type": "function", "id": args.function_id}, {"type": "action", "id": args.action_id}],
        "test_cases": [{"id": "alarm", "name": "告警风险与模拟处置", "input": "设备温度92，请计算风险并安排工单处置",
                        "expected_keywords": ["风险"], "expected_tools": [args.function_id, args.action_id]}]}, expected=201)
    sid = skill["id"]
    assert call("POST", f"/skills/{sid}/validate")["valid"]
    test = call("POST", f"/skills/{sid}/test", {})
    assert test["passed"] and test["validation_level"] == "runtime", test
    release = call("POST", f"/skills/{sid}/publish", {"description": "fresh API runtime test"})
    sv = release.get("version") or release.get("current_version")
    cfg["skill_bindings"] = [{"skill_id": sid, "version": sv}]
    agent = call("POST", "/agents", {"name": "验收设备ReAct助手", "entity_ids": [args.entity_id],
        "system_prompt": "RELEASE_MARKER 根据真实工具结果处理设备告警。", "tools_config": cfg}, expected=201)
    aid = agent["id"]
    def chat(agent_id, question):
        return call("POST", f"/agents/{agent_id}/chat", {"question": question, "stream": False})
    draft = chat(aid, "计算设备风险并安排工单处置")
    assert draft["status"] == "completed", draft
    published = call("POST", f"/agents/{aid}/publish", {"description": "fresh ReAct runtime"})
    assert published["current_version"] == 1
    key = call("GET", f"/agents/{aid}/api-info")["api_key"]
    authorization = client.headers.pop("Authorization")
    try:
        call("POST", f"/open/agents/{aid}/chat", {"question": "计算设备风险", "stream": False}, expected=401)
        public = call("POST", f"/open/agents/{aid}/chat", {"question": "计算设备风险", "stream": False}, headers={"X-Agent-Key": key})
    finally:
        client.headers["Authorization"] = authorization
    assert public["status"] == "completed" and "风险" in public["content"], public
    # Editing invalidates the tested hash. Re-test before a second publication.
    cfg["action_mode"] = "confirm"
    call("PUT", f"/agents/{aid}", {"tools_config": cfg, "system_prompt": "DRAFT_MARKER 根据真实工具结果处理设备告警。"})
    invalid = client.post(f"/api/v1/agents/{aid}/publish", json={})
    assert invalid.status_code == 409
    proposed = chat(aid, "计算设备风险并安排工单处置，请确认")
    assert proposed["status"] == "pending_confirmation" and proposed["pending_actions"], proposed
    pid = proposed["pending_actions"][0]["pending_id"]
    confirmed = call("POST", f"/agents/{aid}/actions/{pid}/confirm", {"approve": True})
    assert confirmed["status"] == "approved", confirmed
    repeat = call("POST", f"/agents/{aid}/actions/{pid}/confirm", {"approve": True})
    assert repeat["result"] == confirmed["result"]
    react_run = call("GET", f"/agents/{aid}/runs/{proposed['id']}")
    assert react_run["status"] == "completed" and react_run["pending_actions"][0]["status"] == "approved", react_run
    call("POST", f"/agents/{aid}/publish", {"description": "confirm flow verified"})
    # Actual graph shares fixed scope and durable approvals; output runs after confirmation.
    graph_cfg = dict(cfg, skill_bindings=[])
    graph = call("POST", "/agents", {"name": "验收设备图助手", "entity_ids": [args.entity_id], "tools_config": graph_cfg,
        "nodes_json": [{"id": "risk", "type": "function", "data": {"function_id": args.function_id, "params": {"temperature": 92}}},
                       {"id": "approval", "type": "human-approval", "data": {"action_id": args.action_id, "params": json.loads(args.action_params)}},
                       {"id": "result", "type": "output", "data": {}}],
        "edges_json": [{"source": "risk", "target": "approval"}, {"source": "approval", "target": "result"}]}, expected=201)
    gid = graph["id"]
    waiting = chat(gid, "告警审批图")
    assert waiting["status"] == "pending_confirmation", waiting
    pid = waiting["pending_actions"][0]["pending_id"]
    graph_confirmation = call("POST", f"/agents/{gid}/actions/{pid}/confirm", {"approve": True})
    assert graph_confirmation["status"] == "approved", graph_confirmation
    resumed = call("GET", f"/agents/{gid}/runs/{waiting['id']}")
    assert resumed["status"] == "completed" and any(t["tool"] == "[output]" for t in resumed["tool_runs"]), resumed
    call("POST", f"/agents/{gid}/publish", {"description": "graph suffix resumed"})
    for run_id in (proposed["id"], waiting["id"]):
        trace = call("GET", f"/traces/{run_id}")
        assert trace["status"] == "ok", trace
    if args.receipt_url:
        assert args.receipt_url.startswith("http://127.0.0.1:"), "Only an isolated receipt service is allowed"
        receipt_response = client.get(args.receipt_url)
        receipt_response.raise_for_status()
        receipts = receipt_response.json()
        for confirmation in (confirmed, graph_confirmation):
            observed = confirmation["result"]["output"]["body"]
            assert observed["ticket"].startswith("FIX-")
            index = int(observed["ticket"].split("-")[1]) - 1
            assert receipts["action_calls"][index] == observed["params"]
        records.append({"method": "GET", "path": args.receipt_url,
                        "status": receipt_response.status_code, "result": receipts,
                        "purpose": "independent business receipt readback; repeat confirmation returned the same ticket"})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"dependency_substitution": "controlled local OpenAI protocol and isolated file-backed HTTP receipt service; real production lifespan/repositories/executors",
        "ids": {"skill": sid, "react_agent": aid, "graph_agent": gid}, "records": records}, ensure_ascii=False, indent=2))
    print(json.dumps({"status": "passed", "skill_id": sid, "react_agent_id": aid, "graph_agent_id": gid, "evidence": str(output)}))


if __name__ == "__main__":
    main()
