import socket
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.datasource import DataSource
from app.schemas.datasource import (
    DataSourceCreate, DataSourceUpdate, DataSourceDetail,
    DataSourceListItem, TestConnectionResult,
    TableListResult, TablePreviewResult,
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
    query = db.query(DataSource)
    if type:
        query = query.filter(DataSource.type == type)
    if status:
        query = query.filter(DataSource.status == status)
    if q:
        query = query.filter(DataSource.name.ilike(f"%{q}%"))
    return query.order_by(DataSource.created_at.desc()).all()


@router.get("/{ds_id}", response_model=DataSourceDetail)
def get_datasource(ds_id: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    return ds


@router.post("", response_model=DataSourceDetail, status_code=201)
def create_datasource(body: DataSourceCreate, db: Session = Depends(get_db)):
    if db.query(DataSource).filter(DataSource.name == body.name).first():
        raise HTTPException(409, "数据源名称已存在")
    ds = DataSource(**body.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    # 尝试获取表数量
    ds.table_count = _count_tables(ds)
    db.commit()
    db.refresh(ds)
    return ds


@router.put("/{ds_id}", response_model=DataSourceDetail)
def update_datasource(ds_id: str, body: DataSourceUpdate, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ds, k, v)
    db.commit()
    db.refresh(ds)
    return ds


@router.delete("/{ds_id}", status_code=204)
def delete_datasource(ds_id: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    db.delete(ds)
    db.commit()


@router.post("/{ds_id}/test", response_model=TestConnectionResult)
def test_connection(ds_id: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    return _test_conn(ds.host, ds.port)


@router.post("/test", response_model=TestConnectionResult)
def test_connection_inline(body: DataSourceCreate):
    return _test_conn(body.host, body.port)


def _test_conn(host: str, port: int) -> dict:
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {e}"}


@router.post("/{ds_id}/toggle", response_model=DataSourceDetail)
def toggle_datasource(ds_id: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    ds.enabled = not ds.enabled
    db.commit()
    db.refresh(ds)
    return ds


@router.post("/{ds_id}/refresh-tables", response_model=DataSourceDetail)
def refresh_tables(ds_id: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    ds.table_count = _count_tables(ds)
    db.commit()
    db.refresh(ds)
    return ds


def _count_tables(ds: DataSource) -> int:
    """连接数据库并查询表数量"""
    try:
        conn = _get_connection(ds)
        if not conn:
            return 0
        cur = conn.cursor()
        if ds.type == "mysql":
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (ds.database,))
        elif ds.type == "postgresql":
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        elif ds.type == "oracle":
            cur.execute("SELECT COUNT(*) FROM user_tables")
        elif ds.type == "sqlserver":
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_type = 'BASE TABLE'")
        else:
            cur.close()
            conn.close()
            return 0
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        logger.warning(f"获取表数量失败 [{ds.name}]: {e}")
        return 0


def _get_connection(ds: DataSource):
    """根据数据源类型创建数据库连接"""
    if ds.type == "mysql":
        import pymysql
        return pymysql.connect(host=ds.host, port=ds.port, user=ds.username, password=ds.password, database=ds.database, connect_timeout=5)
    elif ds.type == "postgresql":
        import psycopg2
        return psycopg2.connect(host=ds.host, port=ds.port, user=ds.username, password=ds.password, dbname=ds.database, connect_timeout=5)
    elif ds.type == "oracle":
        import oracledb
        return oracledb.connect(user=ds.username, password=ds.password, dsn=f"{ds.host}:{ds.port}/{ds.database}")
    elif ds.type == "sqlserver":
        import pymssql
        return pymssql.connect(server=ds.host, port=ds.port, user=ds.username, password=ds.password, database=ds.database, login_timeout=5)
    return None


def _list_tables(ds: DataSource) -> list[str]:
    """获取数据源下所有表名"""
    conn = _get_connection(ds)
    if not conn:
        return []
    cur = conn.cursor()
    if ds.type == "mysql":
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name", (ds.database,))
    elif ds.type == "postgresql":
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
    elif ds.type == "oracle":
        cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
    elif ds.type == "sqlserver":
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_name")
    else:
        cur.close()
        conn.close()
        return []
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tables


def _preview_table(ds: DataSource, table_name: str) -> dict:
    """查询指定表前20条数据"""
    conn = _get_connection(ds)
    if not conn:
        raise HTTPException(400, "不支持的数据源类型")
    cur = conn.cursor()
    # 用反引号/双引号包裹表名防止关键字冲突
    quote = "`" if ds.type == "mysql" else '"'
    cur.execute(f"SELECT * FROM {quote}{table_name}{quote} LIMIT 20")
    columns = [desc[0] for desc in cur.description]
    rows = [list(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return {"table": table_name, "columns": columns, "rows": rows}


@router.get("/{ds_id}/tables", response_model=TableListResult)
def get_tables(ds_id: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    try:
        tables = _list_tables(ds)
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(400, f"获取表列表失败: {e}")


@router.get("/{ds_id}/tables/{table_name}/preview", response_model=TablePreviewResult)
def preview_table(ds_id: str, table_name: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    try:
        return _preview_table(ds, table_name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"查询失败: {e}")
