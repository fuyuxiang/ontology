"""
统一存储服务

从 SystemConfig 读取存储配置，支持本地文件系统和 MinIO 两种后端。
用法：
    from app.services.storage_service import get_storage
    storage = get_storage(db)
    storage.upload(file_bytes, "path/to/file.pdf")
    content = storage.download("path/to/file.pdf")
"""
import logging
import os
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    def upload(self, data: bytes, path: str) -> str:
        """上传文件，返回存储路径"""
        ...

    @abstractmethod
    def download(self, path: str) -> bytes:
        """下载文件，返回文件内容"""
        ...

    @abstractmethod
    def delete(self, path: str) -> bool:
        """删除文件"""
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        ...

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        """列出文件"""
        ...


class LocalBackend(StorageBackend):
    """本地文件系统存储"""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or UPLOAD_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def upload(self, data: bytes, path: str) -> str:
        full_path = os.path.join(self.base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
        return path

    def download(self, path: str) -> bytes:
        full_path = os.path.join(self.base_dir, path)
        with open(full_path, "rb") as f:
            return f.read()

    def delete(self, path: str) -> bool:
        full_path = os.path.join(self.base_dir, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    def exists(self, path: str) -> bool:
        return os.path.exists(os.path.join(self.base_dir, path))

    def list_files(self, prefix: str = "") -> list[str]:
        result = []
        base = os.path.join(self.base_dir, prefix) if prefix else self.base_dir
        if os.path.isdir(base):
            for root, _, files in os.walk(base):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), self.base_dir)
                    result.append(rel.replace("\\", "/"))
        return result


class MinioBackend(StorageBackend):
    """MinIO/S3 对象存储"""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
        import boto3
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        # 确保 bucket 存在
        try:
            self.client.head_bucket(Bucket=bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=bucket)
            except Exception as e:
                logger.warning(f"无法创建 bucket {bucket}: {e}")

    def upload(self, data: bytes, path: str) -> str:
        self.client.put_object(Bucket=self.bucket, Key=path, Body=data)
        return path

    def download(self, path: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=path)
        return resp["Body"].read()

    def delete(self, path: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
            return True
        except Exception:
            return False

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except Exception:
            return False

    def list_files(self, prefix: str = "") -> list[str]:
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"] for obj in resp.get("Contents", [])]


def get_storage(db: Session | None = None) -> StorageBackend:
    """
    获取存储后端实例

    优先从 SystemConfig 读取配置，回退到环境变量。
    """
    backend_type = "local"
    local_path = UPLOAD_DIR
    minio_endpoint = settings.MINIO_ENDPOINT
    minio_access_key = settings.MINIO_ACCESS_KEY
    minio_secret_key = settings.MINIO_SECRET_KEY
    minio_bucket = settings.MINIO_BUCKET

    if db:
        try:
            from app.models.system_config import SystemConfig
            configs = {
                r.key: r.value
                for r in db.query(SystemConfig).filter(SystemConfig.group == "storage").all()
            }
            backend_type = configs.get("storage.backend", backend_type)
            local_path = configs.get("storage.local_path", local_path)
            minio_endpoint = configs.get("storage.minio_endpoint", minio_endpoint)
            minio_access_key = configs.get("storage.minio_access_key", minio_access_key)
            minio_secret_key = configs.get("storage.minio_secret_key", minio_secret_key)
            minio_bucket = configs.get("storage.minio_bucket", minio_bucket)
        except Exception as e:
            logger.warning(f"从数据库读取存储配置失败，使用环境变量: {e}")

    if backend_type == "minio" and minio_endpoint:
        logger.info(f"使用 MinIO 存储: {minio_endpoint}/{minio_bucket}")
        return MinioBackend(
            endpoint=minio_endpoint,
            access_key=minio_access_key or "",
            secret_key=minio_secret_key or "",
            bucket=minio_bucket or "ontology",
        )

    logger.info(f"使用本地存储: {local_path}")
    return LocalBackend(base_dir=local_path)
