"""/connections — Connection 生命周期 API。

替代旧 /datasources 中"连接配置"那部分（不再为每张表自动建记录）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.connectors import ConnectorRegistry
from app.core.deps import require_user
from app.database import get_db
from app.models.user import User
from app.schemas.data_plane import (
    ConnectionCreate,
    ConnectionDetail,
    ConnectionUpdate,
    TestResult,
)
from app.services.data_plane.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["data-plane:connections"])


def _svc(db: Session) -> ConnectionService:
    return ConnectionService(db)


@router.get("", response_model=list[ConnectionDetail])
def list_connections(
    type: str | None = None,
    category: str | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    return _svc(db).list(type=type, category=category, status=status, q=q)


@router.get("/_capabilities")
def list_capabilities():
    """返回 {category: [type, ...]} —— 给前端动态渲染表单 / 类型选择。"""
    return ConnectorRegistry.list_supported()


@router.get("/{conn_id}", response_model=ConnectionDetail)
def get_connection(conn_id: str, db: Session = Depends(get_db)):
    c = _svc(db).get(conn_id)
    if not c:
        raise HTTPException(404, "连接不存在")
    return c


@router.get("/{conn_id}/credential-mask")
def get_credential_mask(conn_id: str, db: Session = Depends(get_db)):
    """返回遮罩凭据，用于编辑表单回显（不暴露明文密码）。"""
    try:
        return _svc(db).get_credential_mask(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.post("", response_model=ConnectionDetail, status_code=201)
def create_connection(
    body: ConnectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    try:
        return _svc(db).create(
            user_id=user.id, **body.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.put("/{conn_id}", response_model=ConnectionDetail)
def update_connection(conn_id: str, body: ConnectionUpdate, db: Session = Depends(get_db)):
    try:
        return _svc(db).update(conn_id, **body.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete("/{conn_id}", status_code=204)
def delete_connection(conn_id: str, cascade: bool = False, db: Session = Depends(get_db)):
    try:
        _svc(db).delete(conn_id, cascade=cascade)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{conn_id}/test", response_model=TestResult)
def test_connection(conn_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).test(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{conn_id}/toggle", response_model=ConnectionDetail)
def toggle_connection(conn_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).toggle(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{conn_id}/databases", response_model=list[str])
def list_databases(conn_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).list_databases(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"列库失败: {e}") from e


@router.get("/{conn_id}/tables", response_model=list[str])
def list_tables(conn_id: str, database: str | None = None, db: Session = Depends(get_db)):
    try:
        return _svc(db).list_tables(conn_id, database)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"列表失败: {e}") from e


@router.get("/{conn_id}/tables/{table_name}/schema")
def get_table_schema(conn_id: str, table_name: str, database: str | None = None,
                    db: Session = Depends(get_db)):
    try:
        cols = _svc(db).get_table_schema(conn_id, table_name, database)
        return {"table": table_name, "columns": cols}
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"获取表结构失败: {e}") from e


@router.get("/{conn_id}/objects")
def list_objects(conn_id: str, prefix: str = "", limit: int = Query(200, ge=1, le=2000),
                 db: Session = Depends(get_db)):
    """对象存储 (S3/OSS/...) 列对象。"""
    try:
        return _svc(db).list_objects(conn_id, prefix=prefix, limit=limit)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"列对象失败: {e}") from e


@router.get("/{conn_id}/paths")
def list_paths(conn_id: str, path: str = "/", limit: int = Query(200, ge=1, le=2000),
               db: Session = Depends(get_db)):
    """文件传输 (FTP/SFTP/...) 列目录。"""
    try:
        return _svc(db).list_paths(conn_id, path=path, limit=limit)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"列目录失败: {e}") from e


@router.get("/{conn_id}/topics", response_model=list[str])
def list_topics(conn_id: str, db: Session = Depends(get_db)):
    """消息队列 (Kafka/...) 列 topic。"""
    try:
        return _svc(db).list_topics(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"列 topic 失败: {e}") from e
