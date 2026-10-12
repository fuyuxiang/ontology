"""Execute a pinned published Agent after the persisted browser server restart."""
import json
import os
from pathlib import Path

import httpx


def main():
    api = os.environ.get("REVIEW_API", "http://127.0.0.1:5055")
    protocol = os.environ.get("REVIEW_PROTOCOL", "http://127.0.0.1:5056")
    assert all(url.startswith("http://127.0.0.1:") for url in (api, protocol))
    evidence = Path("../docs/review/evidence")
    ids = json.loads((evidence / "agd-skills-agent-final.json").read_text())["ids"]
    before = json.loads((evidence / "restart-readback.json").read_text())
    assert before["status"] == "passed"
    aid = ids["react_agent"]
    with httpx.Client(base_url=api, trust_env=False, timeout=60) as client:
        login = client.post("/api/v1/auth/login", json={"username": "admin", "password": os.environ["REVIEW_PASSWORD"]})
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["token"]
        agent_response = client.get(f"/api/v1/agents/{aid}")
        agent_response.raise_for_status()
        agent = agent_response.json()
        pinned = agent["tools_config"]["ontology_version_id"]
        assert pinned == before["after_restart"]["agent"]["fixed_ontology_version_id"]
        assert pinned != before["after_restart"]["active_version_id"]
        key_response = client.get(f"/api/v1/agents/{aid}/api-info")
        key_response.raise_for_status()
        key = key_response.json()["api_key"]
        receipts = httpx.get(protocol + "/fixture/state", trust_env=False).json()["action_calls"]
        response = httpx.post(api + f"/api/v1/open/agents/{aid}/chat", trust_env=False, timeout=60,
                             headers={"X-Agent-Key": key}, json={"question": "计算设备风险", "stream": False})
        response.raise_for_status()
        run = response.json()
        assert run["status"] == "completed" and run["version"] == agent["current_version"]
        assert not run["pending_actions"]
        functions = [row for row in run["tool_runs"] if row["tool"] == "run_function"]
        assert functions and all(row["success"] and row["result"]["value"] == 0.92 for row in functions)
        persisted = client.get(f"/api/v1/agents/{aid}/runs/{run['id']}")
        persisted.raise_for_status()
        assert persisted.json()["status"] == "completed" and persisted.json()["tool_runs"] == run["tool_runs"]
        after = httpx.get(protocol + "/fixture/state", trust_env=False).json()["action_calls"]
        assert after == receipts
        result = {"status": "passed", "agent_id": aid, "agent_version": run["version"],
                  "fixed_ontology_version_id": pinned, "active_ontology_version_id": before["after_restart"]["active_version_id"],
                  "run": {key: run[key] for key in ("id", "status", "version", "tool_runs", "pending_actions")},
                  "receipt_count_before": len(receipts), "receipt_count_after": len(after),
                  "checks": ["pinned old ontology version executed after restart", "real Function risk0.92", "published Agent version used", "run persisted and reread", "no Action side effect"]}
        (evidence / "restart-agent-execution.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": "passed", "run_id": run["id"], "value": 0.92}))


if __name__ == "__main__":
    main()
