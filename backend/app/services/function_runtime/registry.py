from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.models.function import OntologyFunction
from app.services.function_runtime.models import FunctionMeta, ParamSchema

logger = logging.getLogger(__name__)


class FunctionRegistry:
    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[str, FunctionMeta] = {}

    def register(self, meta: FunctionMeta) -> None:
        self._cache[meta.callable_name] = meta
        self._persist(meta)

    def unregister(self, callable_name: str) -> None:
        self._cache.pop(callable_name, None)
        row = self.db.query(OntologyFunction).filter(
            OntologyFunction.callable_name == callable_name,
            OntologyFunction.registered_by == "watcher",
        ).first()
        if row:
            self.db.delete(row)
            self.db.commit()

    def discard(self, callable_name: str) -> None:
        """从内存缓存移除函数（用于 UI 删除后同步运行时状态，不区分登记来源）。"""
        self._cache.pop(callable_name, None)

    def get(self, callable_name: str) -> FunctionMeta | None:
        return self._cache.get(callable_name)

    def list_by_type(
        self, type: Literal["logic", "action"], ontology_id: int | None = None
    ) -> list[FunctionMeta]:
        results = [m for m in self._cache.values() if m.type == type]
        if ontology_id is not None:
            results = [m for m in results if m.ontology_id == ontology_id]
        return results

    def list_capabilities(self, ontology_id: int | None = None) -> list[dict]:
        items = list(self._cache.values())
        if ontology_id is not None:
            items = [m for m in items if m.ontology_id == ontology_id]
        return [
            {
                "name": m.callable_name,
                "description": m.description,
                "type": m.type,
                "params": [
                    {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                    for p in m.params
                ],
                "return_type": m.return_type,
            }
            for m in items
        ]

    def sync_from_db(self) -> None:
        rows = self.db.query(OntologyFunction).filter(
            OntologyFunction.status == "active",
            OntologyFunction.logic_type == "python",
            OntologyFunction.source_path.isnot(None),
        ).all()
        for row in rows:
            params = [
                ParamSchema(
                    name=p.get("name", ""),
                    type=p.get("type", "string"),
                    required=p.get("required", False),
                    description=p.get("description", ""),
                )
                for p in (row.input_schema or [])
                if isinstance(p, dict)
            ]
            meta = FunctionMeta(
                callable_name=row.callable_name,
                description=row.description or "",
                type="action" if "action" in (row.tags or []) else "logic",
                params=params,
                return_type=row.return_type or "object",
                source_path=row.source_path or "",
                func_name=row.func_name or row.callable_name,
                ontology_id=0,
                checksum=row.checksum or "",
            )
            self._cache[meta.callable_name] = meta
        logger.info(f"Registry synced {len(rows)} functions from DB")

    def _persist(self, meta: FunctionMeta) -> None:
        row = self.db.query(OntologyFunction).filter(
            OntologyFunction.callable_name == meta.callable_name,
        ).first()
        if row:
            row.name = meta.callable_name
            row.description = meta.description
            row.input_schema = [
                {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                for p in meta.params
            ]
            row.return_type = meta.return_type
            row.source_path = meta.source_path
            row.func_name = meta.func_name
            row.checksum = meta.checksum
            row.registered_by = "watcher"
            row.status = "active"
            row.logic_type = "python"
        else:
            row = OntologyFunction(
                name=meta.callable_name,
                callable_name=meta.callable_name,
                description=meta.description,
                input_schema=[
                    {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                    for p in meta.params
                ],
                return_type=meta.return_type,
                logic_type="python",
                logic_body="",
                source_path=meta.source_path,
                func_name=meta.func_name,
                checksum=meta.checksum,
                registered_by="watcher",
                status="active",
            )
            self.db.add(row)
        self.db.commit()
