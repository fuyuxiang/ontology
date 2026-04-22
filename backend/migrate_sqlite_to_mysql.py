"""
一次性迁移脚本：SQLite -> MySQL
用法：python migrate_sqlite_to_mysql.py
"""
import sqlite3
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "ontology.db")
MYSQL_URL = "mysql+pymysql://bonc:bonc123@123.56.188.16:3306/ontology_platform?charset=utf8mb4"

from sqlalchemy import create_engine, text
from app.database import Base
from app.models import *  # noqa — 注册所有模型

print("1. 连接 MySQL 并建表...")
mysql_engine = create_engine(MYSQL_URL, echo=False)
Base.metadata.create_all(bind=mysql_engine)
print("   建表完成")

print("2. 读取 SQLite 数据...")
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

tables = [
    "users", "ontology_entities", "entity_attributes", "entity_relations",
    "business_rules", "entity_actions", "audit_log", "datasources",
    "workflows", "workflow_executions", "workflow_apps", "approval_tasks",
    "dashboard_configs", "knowledge_bases", "knowledge_files",
    "model_registry", "agents",
]

with mysql_engine.begin() as mysql_conn:
    # 禁用外键检查，方便批量插入
    mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

    for table in tables:
        try:
            rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        except Exception as e:
            print(f"   跳过 {table}: {e}")
            continue

        if not rows:
            print(f"   {table}: 空表，跳过")
            continue

        # 检查 MySQL 中是否已有数据
        existing = mysql_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        if existing > 0:
            print(f"   {table}: MySQL 已有 {existing} 条，跳过")
            continue

        cols = rows[0].keys()
        placeholders = ", ".join([f":{c}" for c in cols])
        col_names = ", ".join([f"`{c}`" for c in cols])
        sql = text(f"INSERT IGNORE INTO `{table}` ({col_names}) VALUES ({placeholders})")

        data = []
        for row in rows:
            d = dict(row)
            # JSON 字段处理：SQLite 存的是字符串，MySQL 也用 JSON 类型
            for k, v in d.items():
                if isinstance(v, str) and v and v[0] in ('{', '['):
                    try:
                        json.loads(v)  # 验证是合法 JSON，保持字符串形式
                    except Exception:
                        pass
            data.append(d)

        mysql_conn.execute(sql, data)
        print(f"   {table}: 迁移 {len(data)} 条")

    mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

sqlite_conn.close()
print("\n迁移完成！")
