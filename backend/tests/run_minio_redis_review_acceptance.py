"""Actual local MinIO/Redis integration, using only owned disposable services.

Run from backend: python3 tests/run_minio_redis_review_acceptance.py
SystemConfig, uploads, connections and monitor readback use the production app
and lifespan. No driver or successful response is mocked. A bucket and Redis
source key are fixture inputs; application assets/metrics are never preseeded.
Credentials remain in memory or mode-600 Redis config, and are not evidence.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def stop_owned(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def verify_application_restart(asset_id, connection_id, digest):
    """Separate interpreter reopens metadata and decrypts durable credentials."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import SessionLocal
    from app.services.data_plane.asset_service import AssetService
    with TestClient(app) as client:
        auth = client.post("/api/v1/auth/login", json={"username": "admin", "password": "VendorFixture2026!"})
        assert auth.status_code == 200
        client.headers["Authorization"] = "Bearer " + auth.json()["token"]
        detail = client.get(f"/api/v1/assets/{asset_id}")
        assert detail.status_code == 200 and detail.json()["locator"]["source_type"] == "oss"
        preview = client.post(f"/api/v1/assets/{asset_id}/preview")
        assert preview.status_code == 200 and preview.json()["summary"].startswith("Device DEV-001")
        tested = client.post(f"/api/v1/connections/{connection_id}/test")
        assert tested.status_code == 200 and tested.json()["success"]
        with SessionLocal() as db:
            service = AssetService(db)
            actual = service.read_document_content(service.get(asset_id)).encode()
            assert hashlib.sha256(actual).hexdigest() == digest
        services = client.get("/api/v1/monitor/services")
        assert services.status_code == 200
        states = {row["name"]: row["status"] for row in services.json()}
        assert states["MinIO"] == "healthy" and states["Redis"] == "healthy"
    print(json.dumps({"new_interpreter": True, "asset_id": asset_id, "sha256": digest,
                      "durable_metrics": states}), flush=True)


def main():
    import boto3
    from botocore.config import Config
    import httpx
    import redis

    binaries = {name: shutil.which(name) for name in ("minio", "redis-server")}
    if not all(binaries.values()):
        raise RuntimeError("Actual MinIO and Redis executables are required")
    state = Path(tempfile.mkdtemp(prefix="ontology-minio-redis-review-"))
    minio_data, redis_data = state / "minio", state / "redis"
    minio_data.mkdir(); redis_data.mkdir()
    minio_port, console_port, redis_port = free_port(), free_port(), free_port()
    endpoint = f"http://127.0.0.1:{minio_port}"
    access_key, secret_key = "review" + secrets.token_hex(12), secrets.token_hex(32)
    redis_password = secrets.token_hex(32)
    bucket = "ontology-review-" + secrets.token_hex(8)
    versions = {name: subprocess.check_output([binary, "--version"], text=True).splitlines()[0]
                for name, binary in binaries.items()}
    redis_conf = state / "redis.conf"
    redis_conf.write_text(f"bind 127.0.0.1\nport {redis_port}\nprotected-mode yes\n"
        f"dir {redis_data}\ndbfilename review.rdb\nappendonly yes\nappendfsync always\n"
        f"requirepass {redis_password}\ndaemonize no\n")
    redis_conf.chmod(0o600)
    logs = {name: (state / f"{name}.log").open("w") for name in binaries}
    owned = {"minio": None, "redis-server": None}
    minio_env = {**os.environ, "MINIO_ROOT_USER": access_key, "MINIO_ROOT_PASSWORD": secret_key,
                 "MINIO_BROWSER": "off", "MINIO_REGION_NAME": "us-east-1"}
    records = []

    def check(name, **details):
        records.append({"check": name, "passed": True, **details})
        print(json.dumps(records[-1], ensure_ascii=False), flush=True)

    def start_minio():
        owned["minio"] = subprocess.Popen([binaries["minio"], "server", str(minio_data),
            "--address", f"127.0.0.1:{minio_port}", "--console-address", f"127.0.0.1:{console_port}"],
            env=minio_env, stdout=logs["minio"], stderr=logs["minio"])
        with httpx.Client(trust_env=False, timeout=1) as client:
            for _ in range(150):
                if owned["minio"].poll() is not None:
                    raise RuntimeError(f"Owned MinIO stopped; inspect private log at {state / 'minio.log'}")
                try:
                    if client.get(endpoint + "/minio/health/ready").status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
        raise RuntimeError("Isolated MinIO readiness deadline exceeded")

    def start_redis():
        owned["redis-server"] = subprocess.Popen([binaries["redis-server"], str(redis_conf)],
            stdout=logs["redis-server"], stderr=logs["redis-server"])
        for _ in range(100):
            if owned["redis-server"].poll() is not None:
                raise RuntimeError(f"Owned Redis stopped; inspect private log at {state / 'redis-server.log'}")
            try:
                with redis.Redis(host="127.0.0.1", port=redis_port, password=redis_password,
                                 socket_timeout=1, socket_connect_timeout=1) as client:
                    if client.ping():
                        return
            except redis.RedisError:
                pass
            time.sleep(.1)
        raise RuntimeError("Isolated Redis readiness deadline exceeded")

    try:
        start_minio(); start_redis()
        check("actual vendor services started on independent ports", versions=versions,
              minio_port=minio_port, redis_port=redis_port)
        s3 = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1",
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                          connect_timeout=2, read_timeout=3, retries={"max_attempts": 0}))
        s3.create_bucket(Bucket=bucket)
        redis_url = f"redis://:{redis_password}@127.0.0.1:{redis_port}/0"
        with redis.from_url(redis_url) as client:
            client.set("ontology-review:durable", "persistent-source-input")
        try:
            with redis.Redis(host="127.0.0.1", port=redis_port, password="incorrect", socket_timeout=1) as client:
                client.ping()
            raise AssertionError("Redis accepted incorrect credentials")
        except redis.AuthenticationError:
            check("real Redis rejects incorrect credentials")

        unused = free_port()
        os.environ.update(DATABASE_URL=f"sqlite:///{state / 'metadata.db'}", SECRET_KEY=secrets.token_hex(32),
            ADMIN_INITIAL_PASSWORD="VendorFixture2026!", CREDENTIAL_ENCRYPTION_KEY="", WORKSPACE_ROOT=str(state / "workspace"),
            LOCAL_DATA_ROOT=str(state / "local-data"), MONITOR_ENABLED="false", DATA_PLANE_REFRESH_ENABLED="false",
            REDIS_URL=redis_url, MINIO_ENDPOINT="", MINIO_ACCESS_KEY="", MINIO_SECRET_KEY="", MINIO_BUCKET="wrong-env-bucket",
            LLM_BASE_URL=f"http://127.0.0.1:{unused}/v1", LLM_API_KEY="", NEO4J_URI=f"bolt://127.0.0.1:{unused}")
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import SessionLocal
        from app.services.data_plane.asset_service import AssetService
        from app.services.monitor import collector
        from app.config import settings

        def request(client, method, path, body=None, expected=200, **kwargs):
            response = client.request(method, "/api/v1" + path, json=body, **kwargs)
            if response.status_code != expected:
                # Do not echo credential-bearing configuration/auth responses.
                raise AssertionError(f"{method} {path}: expected {expected}, got {response.status_code}")
            return response.json() if response.content else None

        def save_storage(client, secret):
            values = {"backend": "minio", "endpoint": endpoint, "bucket": bucket,
                      "access_key": access_key, "secret_key": secret, "max_upload_mb": "1",
                      "allowed_types": "txt", "local_path": str(state / "uploads")}
            request(client, "PUT", "/system-config", {"group": "storage", "items": [
                {"key": "storage." + key, "value": value} for key, value in values.items()]})

        def collect_and_read(client, expected):
            # Inventory is limited to the two providers under acceptance and the
            # actual metadata DB. Every check, DB save and API response is real.
            collector.SERVICES = [{"name": "MinIO", "check": "minio"},
                                  {"name": "Redis", "check": "redis"}, {"name": "数据库", "check": "db"}]
            settings.MONITOR_ENABLED = True
            client.portal.call(collector.stop_collector)
            before = request(client, "GET", "/monitor/response-history")
            client.portal.call(collector.start_collector)
            try:
                for _ in range(200):
                    history = request(client, "GET", "/monitor/response-history")
                    services = request(client, "GET", "/monitor/services")
                    states = {row["name"]: row["status"] for row in services}
                    if len(history) >= len(before) + 3 and all(states.get(name) == status for name, status in expected.items()):
                        return services
                    time.sleep(.05)
                raise AssertionError("Actual collector metrics did not reach the expected persisted state")
            finally:
                client.portal.call(collector.stop_collector)

        content = ("Device DEV-001 temperature=92 status=alarm\n" * 1700 + "FULL_BODY_END").encode()
        digest = hashlib.sha256(content).hexdigest()
        with TestClient(app) as client:
            auth = request(client, "POST", "/auth/login", {"username": "admin", "password": "VendorFixture2026!"})
            client.headers["Authorization"] = "Bearer " + auth["token"]
            save_storage(client, secret_key)
            config = request(client, "GET", "/system-config")
            assert all(row.get("value") != secret_key for row in config["groups"]["storage"])
            request(client, "PUT", "/system-config", {"group": "storage", "items": [
                {"key": row["key"], "value": row["value"]} for row in config["groups"]["storage"]]})
            asset = request(client, "POST", "/assets/document/upload", expected=201,
                files={"file": ("device-guide.txt", content, "text/plain")}, data={"name": "Real MinIO document"})
            key = asset["locator"]["object_key"]
            assert asset["locator"]["source_type"] == "oss" and asset["locator"]["bucket"] == bucket
            body = s3.get_object(Bucket=bucket, Key=key)["Body"]
            try:
                assert body.read() == content
            finally:
                body.close()
            preview = request(client, "POST", f"/assets/{asset['id']}/preview")
            assert preview["summary"] == content.decode()[:5000]
            with SessionLocal() as db:
                service = AssetService(db)
                assert service.read_document_content(service.get(asset["id"])) == content.decode()
            check("SystemConfig save/read/masked-save drives actual SigV4 upload and full byte readback",
                  asset_id=asset["id"], bytes=len(content), sha256=digest, full_body_beyond_summary=True)

            connection = request(client, "POST", "/connections", {"name": "Actual isolated MinIO", "type": "s3", "category": "object_storage",
                "params": {"endpoint": endpoint, "region": "us-east-1", "bucket": bucket, "path_style": True},
                "credential": {"access_key": access_key, "secret_key": secret_key}}, 201)
            assert request(client, "POST", f"/connections/{connection['id']}/test")["success"]
            objects = request(client, "GET", f"/connections/{connection['id']}/objects")
            assert any(obj["key"] == key and obj["size"] == len(content) for obj in objects)
            check("production S3 connector actual authenticated test/list", connection_id=connection["id"], objects=len(objects))
            healthy = collect_and_read(client, {"MinIO": "healthy", "Redis": "healthy", "数据库": "healthy"})
            check("production collector consumes saved storage and configured Redis URL; metrics API readback", services=healthy)

            count_before = len(request(client, "GET", "/assets"))
            save_storage(client, "incorrect-secret")
            request(client, "POST", "/assets/document/upload", expected=400,
                    files={"file": ("rejected.txt", b"must not register", "text/plain")})
            assert len(request(client, "GET", "/assets")) == count_before
            assert len(s3.list_objects_v2(Bucket=bucket).get("Contents", [])) == 1
            failure = collect_and_read(client, {"MinIO": "unhealthy", "Redis": "healthy"})
            check("invalid real MinIO credentials reject upload without a success asset; health records failure", services=failure)
            save_storage(client, secret_key)

            stop_owned(owned["redis-server"])
            failure = collect_and_read(client, {"MinIO": "healthy", "Redis": "unhealthy"})
            check("real Redis outage becomes unhealthy in persisted metrics/API", services=failure)
            stop_owned(owned["minio"])
            start_minio(); start_redis()
            body = s3.get_object(Bucket=bucket, Key=key)["Body"]
            try:
                assert hashlib.sha256(body.read()).hexdigest() == digest
            finally:
                body.close()
            with redis.from_url(redis_url) as source:
                assert source.get("ontology-review:durable") == b"persistent-source-input"
            assert request(client, "POST", f"/assets/{asset['id']}/preview")["summary"] == content.decode()[:5000]
            recovered = collect_and_read(client, {"MinIO": "healthy", "Redis": "healthy", "数据库": "healthy"})
            check("same data directories restarted; actual object bytes/key persist and collector recovers", sha256=digest, services=recovered)
            assert not collector._collector_tasks
            check("production collector owned tasks stopped")
        restarted = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--readback",
            asset["id"], connection["id"], digest], capture_output=True, text=True, timeout=60)
        if restarted.returncode:
            # Private traceback cannot expose the inherited credential env.
            (state / "application-readback-error.log").write_text(restarted.stderr)
            raise AssertionError(f"New application process readback failed; private log at {state}")
        new_process_result = json.loads(restarted.stdout.strip().splitlines()[-1])
        check("fresh application interpreter/lifespan reopens persisted asset and decrypts credentials",
              **new_process_result)
        s3.close()
        result = {"status": "passed", "state": str(state), "versions": versions, "checks": records,
                  "production_lifespan": True, "prepared_inputs": ["empty bucket", "Redis source key"],
                  "substitutions": ["collector inventory limited to accepted MinIO, Redis and metadata DB"],
                  "not_verified": ["AWS/Aliyun OSS vendors", "remote TLS/certificates", "HA/failover"]}
    finally:
        for process in owned.values():
            stop_owned(process)
        for stream in logs.values():
            stream.close()
    assert all(process is not None and process.poll() is not None for process in owned.values())
    check("only owned MinIO/Redis processes terminated and reaped", exit_codes={
        name: process.returncode for name, process in owned.items()})
    artifact = REPO / "docs/review/evidence/minio-redis-acceptance.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"status": "passed", "checks": len(records), "evidence": str(artifact)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--readback"]:
        verify_application_restart(*sys.argv[2:])
    else:
        main()
