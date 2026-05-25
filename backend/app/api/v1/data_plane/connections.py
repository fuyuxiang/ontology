"""/connections — Connection 生命周期 API。

替代旧 /datasources 中"连接配置"那部分（不再为每张表自动建记录）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.data_plane import (
    ConnectionCreate, ConnectionDetail, ConnectionUpdate, TestResult,
)
from app.services.data_plane.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["data-plane:connections"])


def _svc(db: Session) -> ConnectionService:
    return ConnectionService(db)


@router.get("", response_model=list[ConnectionDetail])
def list_connections(
    type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    return _svc(db).list(type=type, status=status, q=q)


@router.get("/{conn_id}", response_model=ConnectionDetail)
def get_connection(conn_id: str, db: Session = Depends(get_db)):
    c = _svc(db).get(conn_id)
    if not c:
        raise HTTPException(404, "连接不存在")
    return c


@router.post("", response_model=ConnectionDetail, status_code=201)
def create_connection(
    body: ConnectionCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    try:
        return _svc(db).create(
            user_id=user.id if user else None, **body.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/{conn_id}", response_model=ConnectionDetail)
def update_connection(conn_id: str, body: ConnectionUpdate, db: Session = Depends(get_db)):
    try:
        return _svc(db).update(conn_id, **body.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{conn_id}", status_code=204)
def delete_connection(conn_id: str, db: Session = Depends(get_db)):
    try:
        _svc(db).delete(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/{conn_id}/test", response_model=TestResult)
def test_connection(conn_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).test(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.post("/{conn_id}/toggle", response_model=ConnectionDetail)
def toggle_connection(conn_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).toggle(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.get("/{conn_id}/databases", response_model=list[str])
def list_databases(conn_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).list_databases(conn_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"列库失败: {e}")


@router.get("/{conn_id}/tables", response_model=list[str])
def list_tables(conn_id: str, database: str | None = None, db: Session = Depends(get_db)):
    try:
        return _svc(db).list_tables(conn_id, database)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"列表失败: {e}")


@router.get("/{conn_id}/tables/{table_name}/schema")
def get_table_schema(conn_id: str, table_name: str, database: str | None = None,
                    db: Session = Depends(get_db)):
    try:
        cols = _svc(db).get_table_schema(conn_id, table_name, database)
        return {"table": table_name, "columns": cols}
    except LookupError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"获取表结构失败: {e}")
