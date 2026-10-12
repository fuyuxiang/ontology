"""Capture/requery the browser-created business state around a real server restart."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["capture", "verify"])
    parser.add_argument("--api", default="http://127.0.0.1:5055")
    parser.add_argument("--protocol", default="http://127.0.0.1:5056")
    parser.add_argument("--code", default="review_browser_final")
    parser.add_argument("--evidence", default="../docs/review/evidence/restart-readback.json")
    args = parser.parse_args()
    assert all(url.startswith("http://127.0.0.1:") for url in (args.api, args.protocol))
    client = httpx.Client(base_url=args.api, trust_env=False, timeout=30)
    deadline = time.monotonic() + 30
    while True:
        try:
            ready = client.get("/api/health")
            if ready.status_code == 200 and ready.json().get("status") == "ok":
                break
        except (httpx.RequestError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError("Isolated production server did not become ready within 30 seconds")
        time.sleep(0.2)

    def request(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        assert response.status_code == 200, (path, response.status_code)
        return response.json()

    login = request("POST", "/api/v1/auth/login", json={"username": "admin", "password": os.environ["REVIEW_PASSWORD"]})
    client.headers["Authorization"] = "Bearer " + login["token"]
    health = request("GET", "/api/health")
    scenarios = request("GET", "/api/v1/scenarios")
    ontology = next(row for row in scenarios if row["code"] == args.code)
    oid, active = ontology["id"], ontology["active_version_id"]
    assert active and ontology["version_number"] >= 3
    entities = request("GET", "/api/v1/entities", params={"ontology_id": oid})
    entity = next(row for row in entities if row["name"] == "Device")
    eid = entity["id"]
    instance = request("GET", f"/api/v1/ontology-api/objects/{eid}/DEV-001", params={"ontology_id": oid})
    assert instance["temperature"] == 92 and instance["status"] == "maintenance", instance
    groups = request("GET", f"/api/v1/ontology/{oid}/groups")
    assert any(eid in row["entity_ids"] for row in groups)
    tasks = request("GET", f"/api/v1/ontology/{oid}/tasks")
    assert any(row["status"] == "succeeded" and (row["result"] or {}).get("status") == "maintenance" for row in tasks) or any(
        row["status"] == "succeeded" and "maintenance" in json.dumps(row["result"]) for row in tasks), tasks
    receipt_response = httpx.get(args.protocol + "/fixture/state", trust_env=False, timeout=10)
    assert receipt_response.status_code == 200
    receipt = receipt_response.json()["action_calls"]
    assert receipt and all(row["device_id"] == "DEV-001" for row in receipt)
    fresh_path = Path("../docs/review/evidence/agd-skills-agent-final.json")
    fresh = json.loads(fresh_path.read_text())
    sid, aid, gid = (fresh["ids"][key] for key in ("skill", "react_agent", "graph_agent"))
    skill = request("GET", f"/api/v1/skills/{sid}")
    agent = request("GET", f"/api/v1/agents/{aid}")
    graph = request("GET", f"/api/v1/agents/{gid}")
    fixed_version = agent["tools_config"]["ontology_version_id"]
    assert fixed_version != active  # Agent must retain the v2 selected before active v3.
    historic_instance = request("GET", f"/api/v1/ontology-api/objects/{eid}/DEV-001", params={"version_id": fixed_version})
    assert historic_instance["status"] == "maintenance"  # Version freezes mappings/code, not the mutable source rows.
    runs = request("GET", f"/api/v1/agents/{gid}/runs")
    assert any(row["status"] == "completed" for row in runs)
    basic_rows = request("GET", "/api/v1/system-config")["groups"]["basic"]
    basic = {row["key"].removeprefix("basic."): row["value"] for row in basic_rows}
    platform = {key: basic[key] for key in ("system_name", "language", "timezone")}
    if args.mode == "verify":
        assert request("GET", "/api/v1/auth/platform-config") == platform
    summary = {
        "platform_settings": platform,
        "ontology_id": oid, "entity_id": eid, "active_version_id": active,
        "active_version_number": ontology["version_number"], "instance": instance,
        "groups": [{"id": r["id"], "entity_ids": r["entity_ids"]} for r in groups],
        "task_states": {r["id"]: r["status"] for r in tasks}, "receipt_calls": receipt,
        "skill": {"id": sid, "version": skill["current_version"]},
        "agent": {"id": aid, "version": agent["current_version"], "fixed_ontology_version_id": fixed_version},
        "graph": {"id": gid, "version": graph["current_version"], "runs": {r["id"]: r["status"] for r in runs}},
    }
    output = Path(args.evidence)
    if args.mode == "capture":
        evidence = {"status": "captured", "before_restart": summary, "before_health": health}
    else:
        evidence = json.loads(output.read_text())
        assert summary == evidence["before_restart"], "Restart changed persisted state"
        evidence.update(status="passed", after_restart=summary, after_health=health,
                        checks=["same ontology and active v3", "real source maintenance reread", "groups and task states persisted",
                                "HTTP receipt file reloaded", "published Skill/Agent/graph versions retained", "Agent v2 binding stable while ontology active v3",
                                "graph completed run retained", "saved public presentation settings retained"])
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": evidence["status"], "evidence": str(output), "ontology": oid}, ensure_ascii=False))


if __name__ == "__main__":
    main()
