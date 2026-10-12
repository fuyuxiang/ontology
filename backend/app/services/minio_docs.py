"""MinIO 文档读取服务 — 列出并解析 milvus bucket 中的文档"""
from __future__ import annotations

import io
import logging

import boto3
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client(db=None):
    global _client
    if db is not None:
        from app.services.data_plane.storage_policy import storage_policy
        policy = storage_policy(db)
        if not policy["endpoint"]:
            raise ValueError("尚未配置 MinIO 文档源 endpoint")
        return boto3.client("s3", endpoint_url=policy["endpoint"], aws_access_key_id=policy["access_key"], aws_secret_access_key=policy["secret_key"], config=Config(signature_version="s3v4", s3={"addressing_style": "path"}), region_name="us-east-1")
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )
    return _client


def list_documents(prefix: str = "", limit: int = 200, db=None) -> list[dict]:
    client = _get_client(db)
    if db is not None:
        from app.services.data_plane.storage_policy import storage_policy
        bucket = storage_policy(db)["bucket"]
    else:
        bucket = settings.MINIO_BUCKET
    resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=limit)
    items = []
    for obj in resp.get("Contents", []) or []:
        key = obj["Key"]
        if not key.lower().endswith((".docx", ".doc", ".pdf", ".txt", ".md", ".csv", ".xlsx", ".xls", ".pptx", ".ppt")):
            continue
        items.append({
            "key": key,
            "title": key.rsplit("/", 1)[-1],
            "size": obj.get("Size", 0),
            "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
        })
    return items


def get_document_content(key: str, db=None) -> str:
    from app.services.doc_builder import parse_file_content
    client = _get_client(db)
    if db is not None:
        from app.services.data_plane.storage_policy import storage_policy
        policy = storage_policy(db)
        bucket, maximum = policy["bucket"], policy["max_bytes"]
    else:
        bucket, maximum = settings.MINIO_BUCKET, 50 * 1024 * 1024
    response = client.get_object(Bucket=bucket, Key=key)
    try:
        body = response["Body"].read(maximum + 1)
    finally:
        response["Body"].close()
    if len(body) > maximum:
        raise ValueError("文档超过配置的大小限制")
    return parse_file_content(key, body)


def _parse_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        return "[python-docx not installed]"
    except Exception as e:
        logger.warning(f"Failed to parse docx: {e}")
        return f"[Parse error: {e}]"


def _parse_pdf(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=data, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        return "\n".join(text_parts)
    except ImportError:
        return "[PyMuPDF not installed]"
    except Exception as e:
        logger.warning(f"Failed to parse pdf: {e}")
        return f"[Parse error: {e}]"
