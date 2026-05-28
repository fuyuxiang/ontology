"""HTTP API 连接器（用 httpx）。

Connection.params: {base_url, auth_type, default_headers}
credential 按 auth_type 解释：
- bearer:    {token}
- basic:     {username, password}
- api_key:   {key, value, in: header|query}
- none:      {}
"""
from __future__ import annotations

import httpx


def _build_client(params: dict, credential: dict | None) -> httpx.Client:
    base_url = (params.get("base_url") or "").rstrip("/")
    if not base_url:
        raise ValueError("缺少 base_url 参数")
    headers: dict[str, str] = dict(params.get("default_headers") or {})
    cred = credential or {}
    auth = None
    auth_type = (params.get("auth_type") or "none").lower()
    if auth_type == "bearer":
        token = cred.get("token") or ""
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic":
        auth = (cred.get("username") or "", cred.get("password") or "")
    elif auth_type == "api_key":
        loc = (cred.get("in") or "header").lower()
        key = cred.get("key") or "X-API-Key"
        val = cred.get("value") or ""
        if loc == "header" and val:
            headers[key] = val
    return httpx.Client(base_url=base_url, headers=headers, auth=auth, timeout=8.0)


class HTTPApiConnector:
    category = "api"
    type = "rest"

    def test(self, *, params: dict, credential: dict | None) -> tuple[bool, str]:
        try:
            client = _build_client(params, credential)
        except ValueError as e:
            return False, str(e)
        try:
            probe_path = params.get("probe_path") or "/"
            r = client.get(probe_path)
            ok = r.status_code < 500
            return ok, f"HTTP {r.status_code}"
        except httpx.HTTPError as e:
            return False, f"请求失败: {e}"
        except Exception as e:
            return False, f"连接失败: {e}"
        finally:
            try:
                client.close()
            except Exception:
                pass

    def probe(self, *, params: dict, credential: dict | None) -> dict:
        client = _build_client(params, credential)
        try:
            probe_path = params.get("probe_path") or "/"
            r = client.get(probe_path)
            return {
                "status_code": r.status_code,
                "headers": dict(r.headers),
                "preview": r.text[:500],
            }
        finally:
            client.close()
