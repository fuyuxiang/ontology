from __future__ import annotations

import ast
import hashlib
import logging
import os
import re
from pathlib import Path

from app.services.function_runtime.models import FunctionMeta, ParamSchema
from app.services.function_runtime.registry import FunctionRegistry

logger = logging.getLogger(__name__)


class FunctionWatcher:
    def __init__(self, registry: FunctionRegistry, workspace_root: str):
        self.registry = registry
        self.workspace_root = workspace_root
        self._observer = None
        self._file_functions: dict[str, list[str]] = {}

    def start(self) -> None:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class _Handler(FileSystemEventHandler):
                def __init__(self, watcher: FunctionWatcher):
                    self.watcher = watcher

                def on_modified(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        self.watcher._on_file_changed(event.src_path)

                def on_created(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        self.watcher._on_file_changed(event.src_path)

                def on_deleted(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        self.watcher._on_file_deleted(event.src_path)

            self._observer = Observer()
            self._observer.schedule(_Handler(self), self.workspace_root, recursive=True)
            self._observer.daemon = True
            self._observer.start()
            logger.info(f"FunctionWatcher started on {self.workspace_root}")
        except ImportError:
            logger.warning("watchdog not installed, file watching disabled")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("FunctionWatcher stopped")

    def scan_file(self, path: str) -> list[FunctionMeta]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Cannot read {path}: {e}")
            return []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            logger.warning(f"Syntax error in {path}, skipping")
            return []

        checksum = hashlib.md5(code.encode()).hexdigest()
        ontology_id = self._extract_ontology_id(path)
        metas: list[FunctionMeta] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            meta = self._extract_function_meta(node, path, ontology_id, checksum)
            if meta:
                metas.append(meta)

        return metas

    def scan_all(self, ontology_id: int | None = None) -> None:
        root = Path(self.workspace_root)
        if not root.exists():
            return
        for py_file in root.rglob("*.py"):
            metas = self.scan_file(str(py_file))
            for meta in metas:
                if ontology_id is not None and meta.ontology_id != ontology_id:
                    continue
                self.registry.register(meta)
                self._track_file(str(py_file), meta.callable_name)
        logger.info(f"scan_all complete, workspace={self.workspace_root}")

    def _on_file_changed(self, path: str) -> None:
        old_names = set(self._file_functions.get(path, []))
        metas = self.scan_file(path)
        new_names = {m.callable_name for m in metas}

        for meta in metas:
            self.registry.register(meta)

        for removed in old_names - new_names:
            self.registry.unregister(removed)

        self._file_functions[path] = list(new_names)

    def _on_file_deleted(self, path: str) -> None:
        names = self._file_functions.pop(path, [])
        for name in names:
            self.registry.unregister(name)

    def _track_file(self, path: str, callable_name: str) -> None:
        if path not in self._file_functions:
            self._file_functions[path] = []
        if callable_name not in self._file_functions[path]:
            self._file_functions[path].append(callable_name)

    def _extract_ontology_id(self, path: str) -> int:
        return 0

    def _extract_function_meta(
        self, node: ast.FunctionDef, path: str, ontology_id: int, checksum: str
    ) -> FunctionMeta | None:
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if isinstance(func, ast.Name) and func.id != "Function":
                continue
            if isinstance(func, ast.Attribute) and func.attr != "Function":
                continue

            kwargs: dict = {}
            for kw in decorator.keywords:
                val = self._eval_literal(kw.value)
                if val is not None:
                    kwargs[kw.arg] = val

            name = kwargs.get("name")
            if not name:
                continue

            params_raw = kwargs.get("params") or []
            params = [
                ParamSchema(
                    name=p.get("name", ""),
                    type=p.get("type", "string"),
                    required=p.get("required", False),
                    description=p.get("description", ""),
                )
                for p in params_raw
                if isinstance(p, dict)
            ]

            return FunctionMeta(
                callable_name=name,
                description=kwargs.get("description", ""),
                type=kwargs.get("type", "logic"),
                params=params,
                return_type=kwargs.get("return_type", "object"),
                source_path=path,
                func_name=node.name,
                ontology_id=ontology_id,
                checksum=checksum,
            )
        return None

    @staticmethod
    def _eval_literal(node: ast.expr):
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError):
            return None
