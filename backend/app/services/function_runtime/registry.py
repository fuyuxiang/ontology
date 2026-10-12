from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Literal

from sqlalchemy.orm import Session

from app.models.function import OntologyFunction
from app.services.function_runtime.models import FunctionMeta, ParamSchema

logger = logging.getLogger(__name__)


class FunctionRegistry:
    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[str, FunctionMeta] = {}
        self._lock = threading.RLock()

    @contextmanager
    def _session(self):
        # Watcher threads must never borrow the lifecycle/request Session.
        # A factory preserves the configured engine while isolating identity
        # maps and transaction state. Mock registries retain their test double.
        if isinstance(self.db, Session):
            from sqlalchemy.orm import sessionmaker
            with sessionmaker(bind=self.db.get_bind())() as db:
                yield db
        else:
            yield self.db

    def register(self, meta: FunctionMeta) -> None:
        with self._lock:
            if self._persist(meta):
                self._cache[self._key(meta)] = meta
            else:
                self._cache.pop(self._key(meta), None)

    def mutation_lock(self):
        """Serialize source reads, watcher registration, and UI mutations."""
        return self._lock

    @staticmethod
    def _key(meta):
        return f"{meta.ontology_id}:{meta.callable_name}" if meta.ontology_id else meta.callable_name

    def unregister(self, callable_name: str, ontology_id=None) -> None:
        with self._lock, self._session() as db:
            self.discard(callable_name, ontology_id)
            self._delete_registered(db, callable_name, ontology_id)

    def _delete_registered(self, db, callable_name, ontology_id):
        query = db.query(OntologyFunction).filter(
            OntologyFunction.callable_name == callable_name,
            OntologyFunction.registered_by == "watcher",
        )
        if ontology_id:
            query = query.filter(OntologyFunction.ontology_id == str(ontology_id))
        row = query.first()
        if row:
            db.delete(row)
            db.commit()

    def discard(self, callable_name: str, ontology_id=None) -> None:
        """从内存缓存移除函数（用于 UI 删除后同步运行时状态，不区分登记来源）。"""
        with self._lock:
            for key, meta in list(self._cache.items()):
                if (getattr(meta, "callable_name", None) == callable_name or key == callable_name) and (ontology_id is None or str(getattr(meta, "ontology_id", None)) == str(ontology_id)):
                    self._cache.pop(key, None)

    def get(self, callable_name: str, ontology_id=None) -> FunctionMeta | None:
        with self._lock:
            matches = [meta for meta in self._cache.values() if getattr(meta, "callable_name", None) == callable_name
                       and (not ontology_id or str(meta.ontology_id) == str(ontology_id))]
        return matches[0] if len(matches) == 1 else None

    def list_by_type(
        self, type: Literal["logic", "action"], ontology_id: int | None = None
    ) -> list[FunctionMeta]:
        with self._lock:
            results = [m for m in self._cache.values() if m.type == type]
        if ontology_id is not None:
            results = [m for m in results if str(m.ontology_id) == str(ontology_id)]
        return results

    def list_capabilities(self, ontology_id: int | None = None) -> list[dict]:
        with self._lock:
            items = list(self._cache.values())
        if ontology_id is not None:
            items = [m for m in items if str(m.ontology_id) == str(ontology_id)]
        return [
            {
                "name": m.callable_name,
                "description": m.description,
                "type": m.type,
                "params": [
                    {**p.schema, "name": p.name, "type": p.type, "required": p.required, "description": p.description}
                    for p in m.params
                ],
                "return_type": m.return_type,
            }
            for m in items
        ]

    def sync_from_db(self) -> None:
        with self._lock, self._session() as db:
            self._sync_from_db(db)

    def _sync_from_db(self, db) -> None:
        self._cache.clear()
        rows = db.query(OntologyFunction).filter(
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
                    schema=dict(p),
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
                ontology_id=row.ontology_id,
                checksum=row.checksum or "",
            )
            self._cache[self._key(meta)] = meta
        logger.info(f"Registry synced {len(rows)} functions from DB")

    def _persist(self, meta: FunctionMeta) -> None:
        with self._session() as db:
            return self._persist_row(db, meta)

    def _persist_row(self, db, meta):
        query = db.query(OntologyFunction).filter(
            OntologyFunction.callable_name == meta.callable_name,
            OntologyFunction.ontology_id == str(meta.ontology_id) if meta.ontology_id else OntologyFunction.ontology_id.is_(None),
        )
        row = query.first()
        if row:
            # Keep the business display name chosen in the UI when code is rescanned.
            row.name = row.name or meta.callable_name
            row.description = meta.description
            row.input_schema = [
                {**p.schema, "name": p.name, "type": p.type, "required": p.required, "description": p.description}
                for p in meta.params
            ]
            row.return_type = meta.return_type
            row.source_path = meta.source_path
            row.func_name = meta.func_name
            row.checksum = meta.checksum
            row.registered_by = "watcher"
            row.status = getattr(row, "status", None) or "active"
            row.logic_type = "python"
            if meta.ontology_id:
                row.ontology_id = str(meta.ontology_id)
            row.tags = list(dict.fromkeys([*(getattr(row, "tags", None) or []), meta.type]))
        else:
            row = OntologyFunction(
                name=meta.callable_name,
                callable_name=meta.callable_name,
                description=meta.description,
                input_schema=[
                    {**p.schema, "name": p.name, "type": p.type, "required": p.required, "description": p.description}
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
                ontology_id=str(meta.ontology_id) if meta.ontology_id else None,
                tags=[meta.type],
            )
            db.add(row)
        db.commit()
        return row.status == "active"
