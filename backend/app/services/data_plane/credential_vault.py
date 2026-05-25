"""凭据加密引用 — credential vault。

设计原则：
- 业务代码永不持有明文密码；只持有 ref（local-fernet://<id> / vault://path / kms://key-id）
- 唯一允许 fetch 明文的位置：ExecuteService 在执行 SQL 时取出，用完即丢，不缓存
- ConnectionService 创建/更新时调 store/rotate，DB 中只写 ref

本地默认实现 LocalFernetVault：
- 使用 settings.SECRET_KEY 派生 Fernet key
- 密文存 ~/.bonc-ontology/credentials.fernet.json（不入 git）
- 文件失踪/损坏时返回空，调用方需妥善处理（视为凭据丢失，触发 reconnect 流程）
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class CredentialVault(Protocol):
    def store(self, payload: dict) -> str: ...
    def fetch(self, ref: str) -> dict: ...
    def rotate(self, ref: str, payload: dict) -> None: ...
    def delete(self, ref: str) -> None: ...


# ── 本地 Fernet 实现 ─────────────────────────────────────────────

_DEFAULT_VAULT_FILE = Path(os.path.expanduser("~/.bonc-ontology/credentials.fernet.json"))


def _derive_key(secret: str) -> bytes:
    """从 settings.SECRET_KEY 派生 32 字节 Fernet key（base64 编码）。"""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class LocalFernetVault:
    SCHEME = "local-fernet"

    def __init__(self, secret: str | None = None, store_path: Path | None = None):
        self._fernet = Fernet(_derive_key(secret or settings.SECRET_KEY))
        self._path = store_path or _DEFAULT_VAULT_FILE
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text("utf-8") or "{}")
        except Exception:
            logger.exception("vault read failed")
            return {}

    def _write(self, blob: dict[str, str]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(blob), encoding="utf-8")
        tmp.replace(self._path)

    def store(self, payload: dict) -> str:
        token = self._fernet.encrypt(json.dumps(payload).encode("utf-8")).decode("ascii")
        cid = uuid.uuid4().hex
        with self._lock:
            blob = self._read()
            blob[cid] = token
            self._write(blob)
        return f"{self.SCHEME}://{cid}"

    def fetch(self, ref: str) -> dict:
        cid = self._parse(ref)
        with self._lock:
            token = self._read().get(cid)
        if not token:
            return {}
        try:
            return json.loads(self._fernet.decrypt(token.encode("ascii")).decode("utf-8"))
        except InvalidToken:
            logger.error("vault decrypt failed: invalid token for ref=%s", ref)
            return {}

    def rotate(self, ref: str, payload: dict) -> None:
        cid = self._parse(ref)
        token = self._fernet.encrypt(json.dumps(payload).encode("utf-8")).decode("ascii")
        with self._lock:
            blob = self._read()
            blob[cid] = token
            self._write(blob)

    def delete(self, ref: str) -> None:
        cid = self._parse(ref)
        with self._lock:
            blob = self._read()
            if cid in blob:
                del blob[cid]
                self._write(blob)

    @classmethod
    def _parse(cls, ref: str) -> str:
        prefix = f"{cls.SCHEME}://"
        if not ref.startswith(prefix):
            raise ValueError(f"vault ref scheme mismatch: {ref}")
        return ref[len(prefix):]


# ── 工厂 ────────────────────────────────────────────────────────

_vault_singleton: CredentialVault | None = None


def get_vault() -> CredentialVault:
    """根据 settings 选择 vault 实现。当前仅支持 LocalFernetVault。"""
    global _vault_singleton
    if _vault_singleton is None:
        _vault_singleton = LocalFernetVault()
    return _vault_singleton
