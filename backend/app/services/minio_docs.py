"""MinIO 文档读取服务 — 列出并解析 milvus bucket 中的文档"""
from __future__ import annotations

import io
import logging
from typing import Any

import boto3
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
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


def list_documents(prefix: str = "", limit: int = 200) -> list[dict]:
    client = _get_client()
    resp = client.list_objects_v2(Bucket=settings.MINIO_BUCKET, Prefix=prefix, MaxKeys=limit)
    items = []
    for obj in resp.get("Contents", []) or []:
        key = obj["Key"]
        if not key.lower().endswith((".docx", ".doc", ".pdf", ".txt", ".xlsx")):
            continue
        items.append({
            "key": key,
            "title": key.rsplit("/", 1)[-1],
            "size": obj.get("Size", 0),
            "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
        })
    return items


def get_document_content(key: str) -> str:
    client = _get_client()
    resp = client.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
    body = resp["Body"].read()

    if key.lower().endswith(".docx"):
        return _parse_docx(body)
    elif key.lower().endswith(".txt"):
        return body.decode("utf-8", errors="replace")
    elif key.lower().endswith(".pdf"):
        return _parse_pdf(body)
    else:
        return f"[Unsupported format: {key}]"


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
