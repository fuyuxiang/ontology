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


def _get_table_schema(ds: DataSource, table_name: str) -> list[dict]:
    """查询表的列元数据"""
    conn = _get_connection(ds)
    if not conn:
        raise HTTPException(400, "不支持的数据源类型")
    cur = conn.cursor()
    if ds.type == "mysql":
        cur.execute("""
            SELECT c.column_name, c.data_type, c.is_nullable, c.column_comment,
                   CASE WHEN kcu.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name AND kcu.constraint_name = 'PRIMARY'
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """, (ds.database, table_name))
    elif ds.type == "postgresql":
        cur.execute("""
            SELECT c.column_name, c.data_type, c.is_nullable,
                   COALESCE(pgd.description, '') as column_comment,
                   CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM information_schema.columns c
            LEFT JOIN pg_catalog.pg_statio_all_tables st ON st.relname = c.table_name AND st.schemaname = c.table_schema
            LEFT JOIN pg_catalog.pg_description pgd ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
            LEFT JOIN (
                SELECT kcu.column_name FROM information_schema.key_column_usage kcu
                JOIN information_schema.table_constraints tc ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY' AND kcu.table_name = %s AND kcu.table_schema = 'public'
            ) pk ON pk.column_name = c.column_name
            WHERE c.table_schema = 'public' AND c.table_name = %s
            ORDER BY c.ordinal_position
        """, (table_name, table_name))
    elif ds.type == "sqlserver":
        cur.execute("""
            SELECT c.COLUMN_NAME, c.DATA_TYPE, c.IS_NULLABLE, '' as column_comment,
                   CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN (
                SELECT ku.COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' AND ku.TABLE_NAME = %s
            ) pk ON pk.COLUMN_NAME = c.COLUMN_NAME
            WHERE c.TABLE_NAME = %s
            ORDER BY c.ORDINAL_POSITION
        """, (table_name, table_name))
    else:
        cur.close()
        conn.close()
        raise HTTPException(400, f"暂不支持 {ds.type} 的 schema 查询")

    columns = []
    for row in cur.fetchall():
        columns.append({
            "name": row[0],
            "type": row[1],
            "nullable": row[2] in ("YES", "yes", True),
            "comment": row[3] or "",
            "is_pk": bool(row[4]),
        })
    cur.close()
    conn.close()
    return columns


@router.get("/{ds_id}/tables/{table_name}/schema", response_model=TableSchemaResult)
def get_table_schema(ds_id: str, table_name: str, db: Session = Depends(get_db)):
    ds = db.get(DataSource, ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    try:
        columns = _get_table_schema(ds, table_name)
        return {"table": table_name, "columns": columns}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"获取表结构失败: {e}")
