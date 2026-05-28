"""S3 / S3-compatible 对象存储连接器。

依赖 boto3。Connection.params 必填：endpoint（可省略走 AWS 默认）、region、bucket。
credential：{access_key, secret_key}
"""
from __future__ import annotations

from typing import Any

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
    _HAS_BOTO3 = True
except ImportError:
    _HAS_BOTO3 = False


class S3Connector:
    category = "object_storage"
    type = "s3"

    def _client(self, params: dict, credential: dict | None) -> Any:
        if not _HAS_BOTO3:
            raise RuntimeError("S3 连接器需要 boto3，请安装：pip install boto3")
        cred = credential or {}
        cfg = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if params.get("path_style") else "auto"},
        )
        kwargs = dict(
            aws_access_key_id=cred.get("access_key") or None,
            aws_secret_access_key=cred.get("secret_key") or None,
            region_name=params.get("region") or None,
            config=cfg,
        )
        endpoint = params.get("endpoint")
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        return boto3.client("s3", **kwargs)

    def test(self, *, params: dict, credential: dict | None) -> tuple[bool, str]:
        if not _HAS_BOTO3:
            return False, "缺少 boto3 依赖（pip install boto3）"
        bucket = params.get("bucket")
        if not bucket:
            return False, "缺少 bucket 参数"
        try:
            client = self._client(params, credential)
            client.head_bucket(Bucket=bucket)
            return True, "连接成功"
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "Unknown")
            return False, f"S3 错误: {code} - {e}"
        except BotoCoreError as e:
            return False, f"S3 客户端错误: {e}"
        except Exception as e:
            return False, f"连接失败: {e}"

    def list_objects(self, *, params: dict, credential: dict | None,
                     prefix: str = "", limit: int = 200) -> list[dict]:
        bucket = params.get("bucket")
        if not bucket:
            raise ValueError("缺少 bucket 参数")
        client = self._client(params, credential)
        resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=limit)
        items = []
        for obj in resp.get("Contents", []) or []:
            items.append({
                "key": obj["Key"],
                "size": obj.get("Size", 0),
                "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
            })
        return items
