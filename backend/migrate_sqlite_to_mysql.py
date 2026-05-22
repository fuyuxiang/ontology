"""
一次性迁移脚本：SQLite -> MySQL

行为：
1. 用 SQLAlchemy 模型在目标 MySQL 上 create_all（已存在表会跳过）。
2. 自动枚举本地 SQLite 中的所有用户表，按表名搬运数据到 MySQL。
3. 仅迁移 MySQL 端为空的表，避免重复写入。

用法：
    MYSQL_URL='mysql+pymysql://user:pwd@host:port/db?charset=utf8mb4' \
        python migrate_sqlite_to_mysql.py

若未传 MYSQL_URL，使用脚本内置的远端 root 默认值（仅本机一次性迁移用）。
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "ontology.db")
DEFAULT_MYSQL_URL = (
    "mysql+pymysql://root:CeKi%231RgiYuY%25n1p6bQn@10.132.19.82:3318/"
    "ontology_platform?charset=utf8mb4"
)
MYSQL_URL = os.environ.get("MYSQL_URL", DEFAULT_MYSQL_URL)

from sqlalchemy import create_engine, text, inspect as sa_inspect
from app.database import Base
from app.models import *  # noqa — 注册所有模型
from app.models.skill import Skill  # noqa — skills 未在 __init__ 中导出，单独注册

print(f"目标 MySQL: {MYSQL_URL.split('@')[-1]}")

print("1. 连接 MySQL 并建表（按当前 SQLAlchemy 模型）...")
mysql_engine = create_engine(MYSQL_URL, echo=False)
Base.metadata.create_all(bind=mysql_engine)
mysql_inspector = sa_inspect(mysql_engine)
mysql_tables = set(mysql_inspector.get_table_names())
print(f"   建表完成，MySQL 当前共 {len(mysql_tables)} 张表")

print("2. 读取 SQLite 数据...")
if not os.path.exists(SQLITE_PATH):
    print(f"   未找到 {SQLITE_PATH}，跳过数据迁移。")
    sys.exit(0)

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

sqlite_tables = [
    r[0]
    for r in sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
]
print(f"   SQLite 共 {len(sqlite_tables)} 张用户表")

migrated = 0
skipped_no_target = 0
skipped_existing = 0
skipped_empty = 0

with mysql_engine.begin() as mysql_conn:
    mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

    for table in sqlite_tables:
        if table not in mysql_tables:
            print(f"   - {table}: MySQL 无此表，跳过（模型已废弃？）")
            skipped_no_target += 1
            continue

        try:
            rows = sqlite_conn.execute(f"SELECT * FROM `{table}`").fetchall()
        except Exception as e:
            print(f"   - {table}: 读 SQLite 失败 {e}")
            continue

        if not rows:
            print(f"   - {table}: 空表，跳过")
            skipped_empty += 1
            continue

        existing = mysql_conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0
        if existing > 0:
            print(f"   - {table}: MySQL 已有 {existing} 条，跳过")
            skipped_existing += 1
            continue

        cols = list(rows[0].keys())
        placeholders = ", ".join([f":{c}" for c in cols])
        col_names = ", ".join([f"`{c}`" for c in cols])
        sql = text(f"INSERT IGNORE INTO `{table}` ({col_names}) VALUES ({placeholders})")

        data = [dict(r) for r in rows]
        mysql_conn.execute(sql, data)
        print(f"   + {table}: 迁移 {len(data)} 条")
        migrated += 1

    mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

sqlite_conn.close()
print(
    f"\n完成：迁移 {migrated} 张表，跳过空表 {skipped_empty}，"
    f"已存在 {skipped_existing}，无目标表 {skipped_no_target}"
)
