import socket
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.datasource import DataSource
from app.schemas.datasource import (
    DataSourceCreate, DataSourceUpdate, DataSourceDetail,
    DataSourceListItem, TestConnectionResult,
    TableListResult, TablePreviewResult, TableSchemaResult,
)
from app.repositories import DataSourceRepository
from app.services.datasource_utils import (
    get_connection as _get_connection,
    list_tables as _list_tables,
    preview_table as _preview_table,
    get_table_schema as _get_table_schema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasources", tags=["datasources"])


@router.get("", response_model=list[DataSourceListItem])
def list_datasources(
    type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    repo = DataSourceRepository(db)
    return repo.list_with_filters(type=type, status=status, q=q)


@router.get("/{ds_id}", response_model=DataSourceDetail)
def get_datasource(ds_id: str, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    return ds


@router.post("", response_model=list[DataSourceDetail], status_code=201)
def create_datasource(body: DataSourceCreate, db: Session = Depends(get_db)):
    """连接数据库，获取所有表，为每张表创建一条数据源记录"""
    repo = DataSourceRepository(db)
    tmp_ds = DataSource(**body.model_dump(), name="_tmp")
    try:
        tables = _list_tables(tmp_ds)
    except Exception as e:
        raise HTTPException(400, f"连接数据库失败: {e}")
    if not tables:
        raise HTTPException(400, "未获取到任何表，请检查连接信息和权限")

    created = []
    for tbl in tables:
        if repo.find_by_name(tbl):
            continue
        ds = DataSource(
            **body.model_dump(),
            name=tbl,
            table_name=tbl,
            enabled=True,
        )
        repo.create(ds)
        repo.commit()
        repo.refresh(ds)
        created.append(ds)
    return created


@router.put("/{ds_id}", response_model=DataSourceDetail)
def update_datasource(ds_id: str, body: DataSourceUpdate, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ds, k, v)
    repo.commit()
    repo.refresh(ds)
    return ds


@router.delete("/{ds_id}", status_code=204)
def delete_datasource(ds_id: str, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    repo.delete(ds)
    repo.commit()


@router.post("/{ds_id}/test", response_model=TestConnectionResult)
def test_connection(ds_id: str, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    return _test_conn(ds.host, ds.port)


@router.post("/test", response_model=TestConnectionResult)
def test_connection_inline(body: DataSourceCreate):
    return _test_conn(body.host, body.port)


@router.post("/fetch-tables", response_model=TableListResult)
def fetch_tables_inline(body: DataSourceCreate):
    """根据连接信息动态获取数据库中的表列表（无需先创建数据源）"""
    ds = DataSource(**body.model_dump(), name="_tmp")
    try:
        tables = _list_tables(ds)
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(400, f"获取表列表失败: {e}")


def _test_conn(host: str, port: int) -> dict:
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {e}"}


@router.post("/{ds_id}/toggle", response_model=DataSourceDetail)
def toggle_datasource(ds_id: str, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    ds.enabled = not ds.enabled
    repo.commit()
    repo.refresh(ds)
    return ds


@router.post("/{ds_id}/refresh-tables", response_model=DataSourceDetail)
def refresh_tables(ds_id: str, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    if not ds.enabled:
        raise HTTPException(403, "数据源管道已关闭，无法同步数据。请在数据工坊->数据源管理中启用该管道")
    if not ds.table_name:
        raise HTTPException(400, "该数据源未关联数据表，请先编辑选择数据表")
    count, err = _count_records(ds)
    if err:
        raise HTTPException(400, f"同步失败: {err}")
    ds.record_count = count
    repo.commit()
    repo.refresh(ds)
    return ds


def _count_records(ds: DataSource) -> tuple[int, str | None]:
    """连接数据库并查询当前数据表的记录条数"""
    try:
        conn = _get_connection(ds)
        if not conn:
            return 0, f"不支持的数据源类型: {ds.type}"
        cur = conn.cursor()
        quote = "`" if ds.type == "mysql" else '"'
        cur.execute(f"SELECT COUNT(*) FROM {quote}{ds.table_name}{quote}")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count, None
    except Exception as e:
        return 0, str(e)


@router.get("/{ds_id}/preview", response_model=TablePreviewResult)
def preview_datasource(ds_id: str, db: Session = Depends(get_db)):
    """直接预览该数据源关联表的前20条数据"""
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    if not ds.enabled:
        raise HTTPException(403, "数据源管道已关闭，无法读取数据。请在数据工坊->数据源管理中启用该管道")
    if not ds.table_name:
        raise HTTPException(400, "该数据源未关联数据表")
    try:
        return _preview_table(ds, ds.table_name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"查询失败: {e}")


@router.get("/{ds_id}/tables/{table_name}/preview", response_model=TablePreviewResult)
def preview_table(ds_id: str, table_name: str, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    if not ds.enabled:
        raise HTTPException(403, "数据源管道已关闭，无法读取数据。请在数据工坊->数据源管理中启用该管道")
    try:
        return _preview_table(ds, table_name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"查询失败: {e}")


@router.get("/{ds_id}/tables/{table_name}/schema", response_model=TableSchemaResult)
def get_table_schema(ds_id: str, table_name: str, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    ds = repo.get_by_id(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    try:
        columns = _get_table_schema(ds, table_name)
        return {"table": table_name, "columns": columns}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"获取表结构失败: {e}")
