"""一次性迁移脚本：将 local-fernet:// 凭据从本地文件解密后转为 plain:// 存入数据库。

用法: cd backend && python -m scripts.migrate_credentials
"""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text

from app.config import settings

VAULT_FILE = Path(os.path.expanduser("~/.bonc-ontology/credentials.fernet.json"))


def derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def main():
    if not VAULT_FILE.exists():
        print(f"本地凭据文件不存在: {VAULT_FILE}，无需迁移")
        return

    vault_data = json.loads(VAULT_FILE.read_text("utf-8") or "{}")
    if not vault_data:
        print("本地凭据文件为空，无需迁移")
        return

    fernet = Fernet(derive_key(settings.SECRET_KEY))
    engine = create_engine(settings.DATABASE_URL)

    migrated = 0
    failed = 0

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, credential_ref FROM connections WHERE credential_ref LIKE 'local-fernet://%'")
        ).fetchall()

        if not rows:
            print("数据库中没有需要迁移的 local-fernet 凭据")
            return

        print(f"找到 {len(rows)} 条需要迁移的连接记录")

        for row in rows:
            conn_id, ref = row[0], row[1]
            cid = ref.replace("local-fernet://", "")
            token = vault_data.get(cid)

            if not token:
                print(f"  [跳过] connection={conn_id}: 本地文件中找不到凭据 {cid}")
                failed += 1
                continue

            try:
                payload = json.loads(fernet.decrypt(token.encode("ascii")).decode("utf-8"))
            except (InvalidToken, Exception) as e:
                print(f"  [失败] connection={conn_id}: 解密失败 - {e}")
                failed += 1
                continue

            new_ref = "plain://" + base64.urlsafe_b64encode(
                json.dumps(payload, ensure_ascii=False).encode("utf-8")
            ).decode("ascii")

            conn.execute(
                text("UPDATE connections SET credential_ref = :ref, credential_type = 'plain' WHERE id = :id"),
                {"ref": new_ref, "id": conn_id},
            )
            print(f"  [成功] connection={conn_id}: 已迁移")
            migrated += 1

    print(f"\n迁移完成: 成功 {migrated}, 失败 {failed}")


if __name__ == "__main__":
    main()
