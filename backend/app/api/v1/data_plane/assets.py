"""/assets — Asset Catalog API。

包含 5 种 document 接入子路由：
- POST /assets/document/upload
- POST /assets/document/oss
- POST /assets/document/directory
- POST /assets/document/api
- POST /assets/document/mq
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.data_plane import (
    ApiDocCreate, AssetCreate, AssetDetail, AssetUpdate,
    AssetWithUsageOut, DirectoryDocCreate, MqDocCreate,
    OssDocCreate, PreviewOut, QualityMetricOut, SchemaSyncOut,
)
from app.services.data_plane.asset_service import AssetService
from app.services.data_plane.probe_service import ProbeService

router = APIRouter(prefix="/assets", tags=["data-plane:assets"])


def _svc(db: Session) -> AssetService:
    return AssetService(db)


# ── 列表 / 详情 ─────────────────────────────────────────

@router.get("", response_model=list[AssetDetail])
def list_assets(
    kind: str | None = None,
    kinds: str | None = Query(None),
    connection_id: str | None = None,
    domain: str | None = None,
    document_source_type: str | None = None,
    status: str | None = "active",
    q: str | None = None,
    db: Session = Depends(get_db),
):
    kinds_list = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
    return _svc(db).list(
        kind=kind, kinds=kinds_list, connection_id=connection_id, domain=domain,
        document_source_type=document_source_type, status=status, q=q,
    )


@router.get("/scopes", response_model=None)
def list_scopes(db: Session = Depends(get_db)):
    """返回可选的数据范围（数据库连接）列表，仅包含有结构化资产的连接。"""
    from app.models.connection import Connection
    from app.models.asset import Asset

    conns = (
        db.query(Connection)
        .filter(Connection.category == "database")
        .filter(
            Connection.id.in_(
                db.query(Asset.connection_id)
                .filter(Asset.kind.in_(["table", "sql_view"]))
                .filter(Asset.status == "active")
                .filter(Asset.connection_id.isnot(None))
                .distinct()
            )
        )
        .all()
    )
    return {
        "scopes": [
            {
                "id": c.id,
                "name": c.name,
                "display_name": f"{c.name}（{c.type} · {c.database or c.host}）",
                "type": c.type,
                "database": c.database,
            }
            for c in conns
        ]
    }


@router.get("/{asset_id}", response_model=AssetDetail)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    a = _svc(db).get(asset_id)
    if not a:
        raise HTTPException(404, "资产不存在")
    return a


@router.get("/{asset_id}/usage", response_model=AssetWithUsageOut)
def get_asset_usage(asset_id: str, db: Session = Depends(get_db)):
    info = _svc(db).get_with_usage(asset_id)
    if not info:
        raise HTTPException(404, "资产不存在")
    return info


# ── 注册（结构化）─────────────────────────────────────

@router.post("", response_model=AssetDetail, status_code=201)
def create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    try:
        return _svc(db).register(
            user_id=user.id if user else None, **body.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/{asset_id}", response_model=AssetDetail)
def update_asset(asset_id: str, body: AssetUpdate, db: Session = Depends(get_db)):
    try:
        return _svc(db).update(asset_id, **body.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    try:
        _svc(db).delete(asset_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/{asset_id}/deprecate", response_model=AssetDetail)
def deprecate_asset(asset_id: str, reason: str | None = None, db: Session = Depends(get_db)):
    try:
        return _svc(db).deprecate(asset_id, reason)
    except LookupError as e:
        raise HTTPException(404, str(e))


# ── 元数据探测 ────────────────────────────────────────

@router.post("/{asset_id}/sync-schema", response_model=SchemaSyncOut)
def sync_schema(asset_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).sync_schema(asset_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{asset_id}/profile")
def profile_asset(asset_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).profile(asset_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{asset_id}/preview", response_model=PreviewOut)
def preview_asset(asset_id: str, limit: int = 20, db: Session = Depends(get_db)):
    try:
        return _svc(db).preview(asset_id, limit=limit)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"预览失败: {e}")


@router.get("/{asset_id}/quality", response_model=list[QualityMetricOut])
def asset_quality(asset_id: str, since: datetime | None = None, kind: str | None = None,
                  db: Session = Depends(get_db)):
    return ProbeService(db).history(asset_id, kind=kind, limit=200) if not since else \
        ProbeService(db).metrics.list_for_asset(asset_id, kind=kind, since=since)


# ── Document 5 种接入 ─────────────────────────────────

@router.post("/document/upload", response_model=AssetDetail, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    description: str | None = Form(None),
    domain: str | None = Form(None),
    tags: str | None = Form(None),  # JSON 字符串或逗号分隔
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    raw = await file.read()
    tag_list = _parse_tags(tags)
    try:
        return _svc(db).register_document_file(
            file_bytes=raw, filename=file.filename or "uploaded",
            name=name, description=description, domain=domain, tags=tag_list,
            user_id=user.id if user else None,
        )
    except Exception as e:
        raise HTTPException(400, f"上传失败: {e}")


@router.post("/document/oss", response_model=AssetDetail, status_code=201)
def create_oss_doc(body: OssDocCreate, db: Session = Depends(get_db),
                   user: User | None = Depends(get_current_user)):
    try:
        return _svc(db).register_document_oss(user_id=user.id if user else None,
                                               **body.model_dump())
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@router.post("/document/directory", response_model=AssetDetail, status_code=201)
def create_dir_doc(body: DirectoryDocCreate, db: Session = Depends(get_db),
                   user: User | None = Depends(get_current_user)):
    try:
        return _svc(db).register_document_directory(user_id=user.id if user else None,
                                                     **body.model_dump())
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@router.post("/document/api", response_model=AssetDetail, status_code=201)
def create_api_doc(body: ApiDocCreate, db: Session = Depends(get_db),
                   user: User | None = Depends(get_current_user)):
    return _svc(db).register_document_api(user_id=user.id if user else None,
                                           **body.model_dump())


@router.post("/document/mq", response_model=AssetDetail, status_code=201)
def create_mq_doc(body: MqDocCreate, db: Session = Depends(get_db),
                  user: User | None = Depends(get_current_user)):
    return _svc(db).register_document_mq(user_id=user.id if user else None,
                                          **body.model_dump())


# ── 工具 ─────────────────────────────────────────────

def _parse_tags(s: str | None) -> list[str]:
    if not s:
        return []
    s = s.strip()
    if s.startswith("["):
        try:
            import json
            return list(json.loads(s))
        except Exception:
            return []
    return [t.strip() for t in s.split(",") if t.strip()]
