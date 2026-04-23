"""
将 MySQL (ontology_platform) 的所有表结构和数据迁移到 SQLite (ontology.db)
"""
import pymysql
import sqlite3
import os

MYSQL_CONFIG = {
    "host": "110.41.170.155",
    "port": 13306,
    "user": "bonc",
    "password": "LJM2C3LyGNZKKQkyuTXp",
    "database": "ontology_platform",
    "charset": "utf8mb4",
}

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "ontology.db")

MYSQL_TO_SQLITE_TYPE = {
    "int": "INTEGER",
    "bigint": "INTEGER",
    "tinyint": "INTEGER",
    "smallint": "INTEGER",
    "mediumint": "INTEGER",
    "float": "REAL",
    "double": "REAL",
    "decimal": "REAL",
    "varchar": "TEXT",
    "char": "TEXT",
    "text": "TEXT",
    "mediumtext": "TEXT",
    "longtext": "TEXT",
    "json": "TEXT",
    "datetime": "TEXT",
    "timestamp": "TEXT",
    "date": "TEXT",
    "time": "TEXT",
    "blob": "BLOB",
    "mediumblob": "BLOB",
    "longblob": "BLOB",
    "enum": "TEXT",
    "boolean": "INTEGER",
    "bit": "INTEGER",
}


def map_type(mysql_type: str) -> str:
    base = mysql_type.split("(")[0].lower().strip()
    if "unsigned" in base:
        base = base.replace("unsigned", "").strip()
    return MYSQL_TO_SQLITE_TYPE.get(base, "TEXT")


def migrate():
    if os.path.exists(SQLITE_PATH):
        os.remove(SQLITE_PATH)
        print(f"已删除旧文件: {SQLITE_PATH}")

    my = pymysql.connect(**MYSQL_CONFIG)
    sl = sqlite3.connect(SQLITE_PATH)
    sl.execute("PRAGMA journal_mode=WAL;")
    sl.execute("PRAGMA foreign_keys=OFF;")

    my_cur = my.cursor()
    sl_cur = sl.cursor()

    my_cur.execute("SHOW TABLES")
    tables = [row[0] for row in my_cur.fetchall()]
    print(f"发现 {len(tables)} 张表: {tables}\n")

    for table in tables:
        my_cur.execute(f"SHOW COLUMNS FROM `{table}`")
        columns = my_cur.fetchall()

        col_defs = []
        col_names = []
        for col in columns:
            name, col_type, nullable, key, default, extra = col
            col_names.append(name)
            sqlite_type = map_type(col_type)
            parts = [f'"{name}" {sqlite_type}']
            if key == "PRI":
                parts.append("PRIMARY KEY")
                if "auto_increment" in (extra or "").lower():
                    parts.append("AUTOINCREMENT")
            if nullable == "NO" and key != "PRI":
                parts.append("NOT NULL")
            if default is not None:
                if sqlite_type in ("INTEGER", "REAL"):
                    parts.append(f"DEFAULT {default}")
                else:
                    parts.append(f"DEFAULT '{default}'")
            col_defs.append(" ".join(parts))

        create_sql = f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(col_defs) + "\n);"
        sl_cur.execute(create_sql)
        print(f"[{table}] 表已创建")

        my_cur.execute(f"SELECT * FROM `{table}`")
        rows = my_cur.fetchall()
        if rows:
            placeholders = ", ".join(["?"] * len(col_names))
            quoted_cols = ", ".join([f'"{c}"' for c in col_names])
            insert_sql = f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders})'
            converted = []
            for row in rows:
                converted.append(tuple(str(v) if isinstance(v, (bytes, bytearray)) else v for v in row))
            sl_cur.executemany(insert_sql, converted)
            print(f"[{table}] 已导入 {len(rows)} 条数据")
        else:
            print(f"[{table}] 空表，跳过数据导入")

    sl.commit()
    sl.close()
    my.close()
    print(f"\n迁移完成! SQLite 文件: {SQLITE_PATH}")


if __name__ == "__main__":
    migrate()
