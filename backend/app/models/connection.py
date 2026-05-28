"""Connection 模型 — 数据集成模块"连接"一级公民。

替代旧 DataSource 中的物理连接相关字段。仅承载：
- 物理连接信息（endpoint/database/driver/params 因 category 而异）
- 凭据加密引用（credential_ref；明文不入库）
- 连接级权限与限流（writable / pool_size / rate_limit_qps）

不承载：表结构、文件、API、MQ 等"数据集"语义——那归 Asset。
"""
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


# 五大类 + 一个本地上传（无 Connection）
# database         | mysql/postgresql/oracle/sqlserver/hive/clickhouse
# object_storage   | s3/oss/cos/obs/minio
# file_transfer    | ftp/sftp/hdfs
# message_queue    | kafka/pulsar/rocketmq/rabbitmq
# api              | rest/graphql
CATEGORY_DATABASE = "database"
CATEGORY_OBJECT_STORAGE = "object_storage"
CATEGORY_FILE_TRANSFER = "file_transfer"
CATEGORY_MESSAGE_QUEUE = "message_queue"
CATEGORY_API = "api"


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default=CATEGORY_DATABASE)
        # 五大类，决定 type 取值范围与 params 的有效字段
    type: Mapped[str] = mapped_column(String(30), nullable=False)
        # database: mysql | postgresql | oracle | sqlserver | hive | clickhouse
        # object_storage: s3 | oss | cos | obs | minio
        # file_transfer: ftp | sftp | hdfs
        # message_queue: kafka | pulsar | rocketmq | rabbitmq
        # api: rest | graphql

    # ── DB 类专用字段（其它 category 留默认值）──
    host: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    database: Mapped[str] = mapped_column(String(120), default="")

    # ── 通用扩展字段：所有非 DB 类型把 endpoint/region/bucket/brokers/base_url 等下沉到这里 ──
    params: Mapped[dict | None] = mapped_column(JSON)
        # database:        {charset, ssl_ca, schema, sid, jdbc_extra}
        # object_storage:  {endpoint, region, bucket, path_style}
        # file_transfer:   {root_path, passive (ftp), use_tls}
        # message_queue:   {brokers: "h1:9092,h2:9092", security_protocol, sasl_mechanism}
        # api:             {base_url, auth_type: bearer|basic|oauth2, headers}

    # ── 凭据：明文不入库，只存引用 ──
    credential_ref: Mapped[str] = mapped_column(String(300), default="")
        # local-fernet://<id> | vault://path | kms://key-id
    credential_type: Mapped[str] = mapped_column(String(30), default="local-fernet")

    # ── 连接级安全/限流 ──
    writable: Mapped[bool] = mapped_column(Boolean, default=False)
    pool_size: Mapped[int] = mapped_column(Integer, default=4)
    rate_limit_qps: Mapped[int] = mapped_column(Integer, default=20)

    # ── 状态/元信息 ──
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
        # active | inactive | error
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_test_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    last_test_message: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))


Index("ix_connections_category_type", Connection.category, Connection.type)
Index("ix_connections_status_enabled", Connection.status, Connection.enabled)
