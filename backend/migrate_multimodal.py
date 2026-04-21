"""迁移脚本：为 datasources 表添加多模态字段（幂等）"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine

COLUMNS = [
    ("source_category", "VARCHAR(20) DEFAULT 'database'"),
    ("file_path", "VARCHAR(500)"),
    ("file_type", "VARCHAR(20)"),
    ("api_url", "VARCHAR(500)"),
    ("api_method", "VARCHAR(10) DEFAULT 'GET'"),
    ("api_headers", "TEXT"),
    ("api_body", "TEXT"),
    ("mq_topic", "VARCHAR(200)"),
    ("mq_group", "VARCHAR(200)"),
    ("poll_interval", "INTEGER DEFAULT 60"),
    ("parsed_content", "TEXT"),
]

with engine.connect() as conn:
    existing = {row[1] for row in conn.execute(
        __import__('sqlalchemy').text("PRAGMA table_info(datasources)")
    )}
    for col, col_type in COLUMNS:
        if col not in existing:
            conn.execute(__import__('sqlalchemy').text(
                f"ALTER TABLE datasources ADD COLUMN {col} {col_type}"
            ))
            print(f"  Added column: {col}")
        else:
            print(f"  Already exists: {col}")
    conn.commit()

print("Migration complete.")
