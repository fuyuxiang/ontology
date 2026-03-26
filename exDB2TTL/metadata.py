"""数据库与样例 CSV 元数据抽取逻辑。"""

from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .config import ConfigError, DatabaseConfig
from .models import ColumnMeta, DatabaseMetadata, ForeignKeyMeta, TableMeta


def extract_metadata(config: DatabaseConfig) -> DatabaseMetadata:
    """根据数据库方言选择对应的元数据抽取策略。"""
    dialect = config.dialect.lower()
    if dialect == "sqlite":
        return _extract_sqlite_metadata(config)
    if dialect in {"csv", "csv_samples"}:
        return _extract_csv_metadata(config)
    if dialect in {"postgresql", "postgres"}:
        raise ConfigError(
            "PostgreSQL extraction is not enabled in this environment. "
            "Either add a driver and extend exDB2TTL/metadata.py, or provide metadata.json manually."
        )
    if dialect == "mysql":
        return _extract_mysql_metadata(config)
    raise ConfigError(f"Unsupported database dialect: {config.dialect}")


def _extract_sqlite_metadata(config: DatabaseConfig) -> DatabaseMetadata:
    """从 SQLite 数据库中抽取表结构、主键、外键和样例数据。"""
    if not config.sqlite_path:
        raise ConfigError("database.sqlite_path is required when dialect=sqlite")
    database_path = Path(config.sqlite_path)
    if not database_path.exists():
        raise ConfigError(f"SQLite database file not found: {database_path}")

    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    try:
        tables: list[TableMeta] = []
        known_tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [table for table in config.tables if table not in known_tables]
        if missing:
            raise ConfigError(f"Tables not found in SQLite database: {', '.join(missing)}")

        for table_name in config.tables:
            tables.append(_extract_sqlite_table(connection, config, table_name))

        return DatabaseMetadata(
            database_name=config.database_name,
            dialect=config.dialect,
            schema=config.schema,
            tables=tables,
        )
    finally:
        connection.close()


def _extract_csv_metadata(config: DatabaseConfig) -> DatabaseMetadata:
    """仅根据 CSV 表头和样例行推断弱元数据。"""
    csv_dir = _require_sample_csv_dir(config)
    tables: list[TableMeta] = []
    for table_name in config.tables:
        fieldnames, sample_rows = _load_csv_table(csv_dir / f"{table_name}.csv", config.sample_rows, config.sample_csv_encoding)
        tables.append(
            TableMeta(
                name=table_name,
                columns=_infer_csv_columns(fieldnames, sample_rows),
                primary_keys=[],
                foreign_keys=[],
                comment=None,
                sample_rows=sample_rows,
            )
        )
    return DatabaseMetadata(
        database_name=config.database_name,
        dialect=config.dialect,
        schema=config.schema,
        tables=tables,
    )


def _extract_mysql_metadata(config: DatabaseConfig) -> DatabaseMetadata:
    """从 MySQL 信息模式和样例数据中构建元数据对象。"""
    try:
        import pymysql
    except ImportError as exc:
        raise ConfigError(
            "MySQL extraction requires pymysql. Install it first, "
            "or switch database.dialect to 'csv' and provide sample_csv_dir."
        ) from exc

    connection = pymysql.connect(**_mysql_connection_kwargs(config), cursorclass=pymysql.cursors.DictCursor)
    try:
        table_rows = _mysql_query_table_rows(connection, config)
        table_comments = {row["TABLE_NAME"]: _normalize_optional_string(row["TABLE_COMMENT"]) for row in table_rows}
        existing_tables = set(table_comments)
        missing = [table for table in config.tables if table not in existing_tables]
        if missing:
            raise ConfigError(f"Tables not found in MySQL database: {', '.join(missing)}")

        column_rows = _mysql_query_columns(connection, config)
        fk_rows = _mysql_query_foreign_keys(connection, config)

        columns_by_table: dict[str, list[dict]] = defaultdict(list)
        for row in column_rows:
            columns_by_table[row["TABLE_NAME"]].append(row)

        fks_by_table: dict[str, list[dict]] = defaultdict(list)
        for row in fk_rows:
            fks_by_table[row["TABLE_NAME"]].append(row)

        tables: list[TableMeta] = []
        for table_name in config.tables:
            sample_rows = _resolve_sample_rows(
                config,
                table_name,
                lambda current_table=table_name: _mysql_query_sample_rows(connection, current_table, config.sample_rows),
            )

            primary_keys: list[tuple[int, str]] = []
            columns: list[ColumnMeta] = []
            for row in columns_by_table.get(table_name, []):
                is_pk = row["COLUMN_KEY"] == "PRI"
                if is_pk:
                    primary_keys.append((int(row["ORDINAL_POSITION"]), row["COLUMN_NAME"]))
                columns.append(
                    ColumnMeta(
                        name=row["COLUMN_NAME"],
                        data_type=(row["DATA_TYPE"] or "").upper() or "TEXT",
                        nullable=False if is_pk else row["IS_NULLABLE"] == "YES",
                        primary_key=is_pk,
                        default=None if row["COLUMN_DEFAULT"] is None else str(row["COLUMN_DEFAULT"]),
                        comment=_normalize_optional_string(row["COLUMN_COMMENT"]),
                        enum_values=_parse_mysql_enum_values(row["COLUMN_TYPE"] or ""),
                    )
                )

            foreign_keys = [
                ForeignKeyMeta(
                    column_name=row["COLUMN_NAME"],
                    target_table=row["REFERENCED_TABLE_NAME"],
                    target_column=row["REFERENCED_COLUMN_NAME"],
                    constraint_name=row["CONSTRAINT_NAME"],
                )
                for row in fks_by_table.get(table_name, [])
            ]

            tables.append(
                TableMeta(
                    name=table_name,
                    columns=columns,
                    primary_keys=[name for _, name in sorted(primary_keys)],
                    foreign_keys=foreign_keys,
                    comment=table_comments.get(table_name),
                    sample_rows=sample_rows,
                )
            )

        return DatabaseMetadata(
            database_name=config.database_name,
            dialect=config.dialect,
            schema=config.schema,
            tables=tables,
        )
    finally:
        connection.close()


def _extract_sqlite_table(connection: sqlite3.Connection, config: DatabaseConfig, table_name: str) -> TableMeta:
    """抽取单张 SQLite 表的结构和样例数据。"""
    quoted_table = _quote_sqlite_identifier(table_name)
    column_rows = connection.execute(f'PRAGMA table_info("{quoted_table}")').fetchall()
    fk_rows = connection.execute(f'PRAGMA foreign_key_list("{quoted_table}")').fetchall()
    sample_rows_payload = _resolve_sample_rows(
        config,
        table_name,
        lambda: [dict(row) for row in connection.execute(f'SELECT * FROM "{quoted_table}" LIMIT {int(config.sample_rows)}').fetchall()],
    )

    columns: list[ColumnMeta] = []
    primary_keys: list[tuple[int, str]] = []
    for row in column_rows:
        is_pk = bool(row["pk"])
        if is_pk:
            primary_keys.append((int(row["pk"]), row["name"]))
        columns.append(
            ColumnMeta(
                name=row["name"],
                data_type=row["type"] or "TEXT",
                nullable=False if is_pk else not bool(row["notnull"]),
                primary_key=is_pk,
                default=None if row["dflt_value"] is None else str(row["dflt_value"]),
                comment=None,
                enum_values=[],
            )
        )

    foreign_keys = [
        ForeignKeyMeta(
            column_name=row["from"],
            target_table=row["table"],
            target_column=row["to"],
            constraint_name=f"{table_name}_fk_{row['id']}_{row['seq']}",
        )
        for row in fk_rows
    ]

    return TableMeta(
        name=table_name,
        columns=columns,
        primary_keys=[name for _, name in sorted(primary_keys)],
        foreign_keys=foreign_keys,
        comment=None,
        sample_rows=sample_rows_payload,
    )


def _quote_sqlite_identifier(value: str) -> str:
    """转义 SQLite 标识符中的双引号。"""
    return value.replace('"', '""')


def _require_sample_csv_dir(config: DatabaseConfig) -> Path:
    """校验样例 CSV 目录存在。"""
    if not config.sample_csv_dir:
        raise ConfigError("database.sample_csv_dir is required for csv-based extraction")
    sample_dir = Path(config.sample_csv_dir)
    if not sample_dir.exists() or not sample_dir.is_dir():
        raise ConfigError(f"CSV sample directory not found: {sample_dir}")
    return sample_dir


def _resolve_sample_rows(config: DatabaseConfig, table_name: str, db_loader) -> list[dict]:
    """优先使用外部样例 CSV，缺失时再从数据库读取样例行。"""
    csv_rows = _load_sample_rows_from_csv_dir(config, table_name)
    if csv_rows is not None:
        return csv_rows
    return db_loader()


def _load_sample_rows_from_csv_dir(config: DatabaseConfig, table_name: str) -> list[dict] | None:
    """从样例 CSV 目录读取单表样例数据。"""
    if not config.sample_csv_dir:
        return None
    sample_path = Path(config.sample_csv_dir) / f"{table_name}.csv"
    if not sample_path.exists():
        return None
    _, rows = _load_csv_table(sample_path, config.sample_rows, config.sample_csv_encoding)
    return rows


def _load_csv_table(path: Path, sample_rows: int, encoding: str) -> tuple[list[str], list[dict]]:
    """读取单个 CSV 文件的表头和前若干行样例。"""
    if not path.exists():
        raise ConfigError(f"CSV sample file not found: {path}")

    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ConfigError(f"CSV sample file is missing a header row: {path}")

        rows: list[dict] = []
        for index, row in enumerate(reader):
            if index >= sample_rows:
                break
            rows.append({field: _normalize_csv_value(row.get(field)) for field in fieldnames})
    return fieldnames, rows


def _normalize_csv_value(value):
    """保留 CSV 字段的原始文本形态，空值仍记为 `None`。"""
    if value is None:
        return None
    text = str(value)
    return text


def _infer_csv_columns(fieldnames: list[str], sample_rows: list[dict]) -> list[ColumnMeta]:
    """根据样例值推断 CSV 列的数据类型与可空性。"""
    columns: list[ColumnMeta] = []
    for field in fieldnames:
        values = [row.get(field) for row in sample_rows]
        columns.append(
            ColumnMeta(
                name=field,
                data_type=_infer_csv_data_type(values),
                nullable=any(value in (None, "") for value in values) or not values,
                primary_key=False,
                default=None,
                comment=None,
                enum_values=[],
            )
        )
    return columns


def _infer_csv_data_type(values: list[object]) -> str:
    """基于样例值做简单类型推断。"""
    non_empty = [str(value).strip() for value in values if value not in (None, "")]
    if not non_empty:
        return "TEXT"
    if all(_looks_like_bool(value) for value in non_empty):
        return "BOOLEAN"
    if all(_looks_like_int(value) for value in non_empty):
        return "INTEGER"
    if all(_looks_like_float(value) for value in non_empty):
        return "REAL"
    return "TEXT"


def _looks_like_bool(value: str) -> bool:
    """判断字符串是否形似布尔值。"""
    return value.lower() in {"0", "1", "true", "false", "yes", "no", "y", "n"}


def _looks_like_int(value: str) -> bool:
    """判断字符串是否形似整数。"""
    try:
        int(value)
    except ValueError:
        return False
    return True


def _looks_like_float(value: str) -> bool:
    """判断字符串是否形似浮点数。"""
    try:
        float(value)
    except ValueError:
        return False
    return True


def _mysql_connection_kwargs(config: DatabaseConfig) -> dict:
    """组装 MySQL 连接参数，兼容 URL 和离散字段两种配置方式。"""
    if config.connection_url:
        parsed = urlparse(config.connection_url)
        if parsed.scheme not in {"mysql", "mysql+pymysql"}:
            raise ConfigError("database.connection_url must use mysql:// or mysql+pymysql:// for MySQL extraction")
        query = parse_qs(parsed.query)
        password = parsed.password or _password_from_env(config.password_env)
        database_name = parsed.path.lstrip("/") or config.database_name
        return {
            "host": parsed.hostname or config.host or "127.0.0.1",
            "port": parsed.port or config.port or 3306,
            "user": unquote(parsed.username) if parsed.username else config.username,
            "password": unquote(password) if password else password,
            "database": database_name,
            "charset": query.get("charset", [config.mysql_charset])[0],
            "autocommit": True,
        }

    if not config.host:
        raise ConfigError("database.host is required for MySQL extraction")
    if not config.username:
        raise ConfigError("database.username is required for MySQL extraction")
    return {
        "host": config.host,
        "port": config.port or 3306,
        "user": config.username,
        "password": _password_from_env(config.password_env),
        "database": config.database_name,
        "charset": config.mysql_charset,
        "autocommit": True,
    }


def _password_from_env(password_env: str | None) -> str | None:
    """从环境变量中读取数据库密码。"""
    if not password_env:
        return None
    from os import getenv

    value = getenv(password_env)
    if value is None:
        raise ConfigError(f"Environment variable {password_env} is required for database password")
    return value


def _mysql_query_table_rows(connection, config: DatabaseConfig) -> list[dict]:
    """查询目标表的表级元数据。"""
    placeholders = ", ".join(["%s"] * len(config.tables))
    sql = f"""
        SELECT TABLE_NAME, TABLE_COMMENT
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME IN ({placeholders})
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [config.database_name, *config.tables])
        return list(cursor.fetchall())


def _mysql_query_columns(connection, config: DatabaseConfig) -> list[dict]:
    """查询目标表的字段元数据。"""
    placeholders = ", ".join(["%s"] * len(config.tables))
    sql = f"""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE,
               COLUMN_KEY, COLUMN_DEFAULT, COLUMN_COMMENT, ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME IN ({placeholders})
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [config.database_name, *config.tables])
        return list(cursor.fetchall())


def _mysql_query_foreign_keys(connection, config: DatabaseConfig) -> list[dict]:
    """查询目标表的外键约束信息。"""
    placeholders = ", ".join(["%s"] * len(config.tables))
    sql = f"""
        SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME,
               REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME IN ({placeholders})
          AND REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [config.database_name, *config.tables])
        return list(cursor.fetchall())


def _mysql_query_sample_rows(connection, table_name: str, limit: int) -> list[dict]:
    """读取单表的少量样例数据。"""
    escaped_table = table_name.replace("`", "``")
    sql = f"SELECT * FROM `{escaped_table}` LIMIT {int(limit)}"
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return list(cursor.fetchall())


def _parse_mysql_enum_values(column_type: str) -> list[str]:
    """从 MySQL ENUM 定义中提取可选值列表。"""
    normalized = column_type.strip()
    if not normalized.lower().startswith("enum(") or not normalized.endswith(")"):
        return []
    inner = normalized[5:-1]
    if not inner:
        return []
    reader = csv.reader([inner], delimiter=",", quotechar="'", escapechar="\\")
    values = next(reader, [])
    return [value.replace("''", "'") for value in values]


def _normalize_optional_string(value: object) -> str | None:
    """把可选文本值标准化为空或去首尾空白后的字符串。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
