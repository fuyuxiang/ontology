"""凭据存储 — credential vault。

FernetVault 实现：
- 凭据使用 Fernet 对称加密后存入 credential_ref 字段
- 加密密钥从环境变量 CREDENTIAL_ENCRYPTION_KEY 读取
- ref 格式: fernet://<encrypted_base64>
- 兼容读取旧 plain:// 格式（读时自动迁移）
"""
from __future__ import annotations

import base64
import json
import logging
import hashlib
from typing import Protocol

logger = logging.getLogger(__name__)


class CredentialVault(Protocol):
    def store(self, payload: dict) -> str: ...
    def fetch(self, ref: str) -> dict: ...
    def rotate(self, ref: str, payload: dict) -> str: ...
    def delete(self, ref: str) -> None: ...


class PlainTextVault:
    """Legacy: 仅用于读取旧格式"""
    SCHEME = "plain"

    def fetch(self, ref: str) -> dict:
        if not ref:
            return {}
        prefix = f"{self.SCHEME}://"
        if not ref.startswith(prefix):
            return {}
        data = ref[len(prefix):]
        try:
            return json.loads(base64.urlsafe_b64decode(data).decode("utf-8"))
        except Exception:
            raise ValueError("旧版凭据无法读取，请重新保存连接凭据") from None


class FernetVault:
    SCHEME = "fernet"

    def __init__(self, key: str):
        from cryptography.fernet import Fernet
        if not key:
            raise ValueError("凭据加密需要稳定的 CREDENTIAL_ENCRYPTION_KEY")
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        self._plain_vault = PlainTextVault()

    def store(self, payload: dict) -> str:
        plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        encrypted = self._fernet.encrypt(plaintext).decode("ascii")
        return f"{self.SCHEME}://{encrypted}"

    def fetch(self, ref: str) -> dict:
        if not ref:
            return {}
        if ref.startswith("plain://"):
            return self._plain_vault.fetch(ref)
        prefix = f"{self.SCHEME}://"
        if not ref.startswith(prefix):
            raise ValueError("不支持的凭据格式，请重新保存连接凭据")
        data = ref[len(prefix):]
        try:
            decrypted = self._fernet.decrypt(data.encode("ascii"))
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            raise ValueError("凭据解密失败：密钥已变化或记录损坏，请恢复原密钥或重新保存凭据") from None

    def rotate(self, ref: str, payload: dict) -> str:
        return self.store(payload)

    def delete(self, ref: str) -> None:
        pass


# ── 工厂 ────────────────────────────────────────────────────────

_vault_singleton: CredentialVault | None = None


def get_vault() -> CredentialVault:
    global _vault_singleton
    if _vault_singleton is None:
        from app.config import settings
        key = settings.CREDENTIAL_ENCRYPTION_KEY or base64.urlsafe_b64encode(
            hashlib.sha256(("ontology:credentials:v1:" + settings.SECRET_KEY).encode()).digest()).decode()
        _vault_singleton = FernetVault(key)
    return _vault_singleton
