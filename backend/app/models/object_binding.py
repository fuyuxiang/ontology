"""ObjectBinding — ObjectType ↔ Asset 的强类型映射。

替代旧 EntityAttribute.source_table/source_field 字符串方案。
归本体建模模块拥有，但模型放在共享层便于双向引用：
- 建模侧：BindingTab 在此 CRUD
- 数据集成侧：删 Asset 前查引用、画 Asset→ObjectType 血缘
- AI 自动构建：发布时自动落 Binding（来自草稿的 backing_asset_ids）

兼容期：写 Binding 时，事件 handler 同步反写 EntityAttribute.source_table/source_field（M1~M3）。
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class ObjectBinding(Base):
    __tablename__ = "object_bindings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    object_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ontology_entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
        # primary | enrichment | document_evidence

    field_mappings: Mapped[list] = mapped_column(JSON, default=list)
        # [{"attribute_id":"...","source_column":"user_id","transform":null}, ...]
    id_column: Mapped[str | None] = mapped_column(String(120))
        # 主键列（来自 asset.schema_snapshot）
    filter_expr: Mapped[str | None] = mapped_column(Text)
        # 可选：限定该 Object 仅取此 Asset 中满足条件的行（参数化 WHERE 片段）

    status: Mapped[str] = mapped_column(String(20), default="active")
        # active | needs_review（schema 漂移触发） | deprecated
    review_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))

    __table_args__ = (
        UniqueConstraint("object_type_id", "asset_id", "role", name="uq_object_binding"),
    )


Index("ix_binding_status", ObjectBinding.status)
