"""凭据存储 — credential vault。

PlainTextVault 实现：
- 凭据以 base64(json) 直接编码进 credential_ref 字段
- 数据完全存在数据库中，跨机器部署无障碍
- ref 格式: plain://<base64url_json>
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class CredentialVault(Protocol):
    def store(self, payload: dict) -> str: ...
    def fetch(self, ref: str) -> dict: ...
    def rotate(self, ref: str, payload: dict) -> str: ...
    def delete(self, ref: str) -> None: ...


class PlainTextVault:
    SCHEME = "plain"

    def store(self, payload: dict) -> str:
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        return f"{self.SCHEME}://{encoded}"

    def fetch(self, ref: str) -> dict:
        if not ref:
            return {}
        prefix = f"{self.SCHEME}://"
        if not ref.startswith(prefix):
            logger.error("vault ref scheme mismatch: %s", ref[:40])
            return {}
        data = ref[len(prefix):]
        try:
            return json.loads(base64.urlsafe_b64decode(data).decode("utf-8"))
        except Exception:
            logger.error("vault decode failed for ref=%s", ref[:40])
            return {}

    def rotate(self, ref: str, payload: dict) -> str:
        return self.store(payload)

    def delete(self, ref: str) -> None:
        pass


# ── 工厂 ────────────────────────────────────────────────────────

_vault_singleton: CredentialVault | None = None


def get_vault() -> CredentialVault:
    global _vault_singleton
    if _vault_singleton is None:
        _vault_singleton = PlainTextVault()
    return _vault_singleton
