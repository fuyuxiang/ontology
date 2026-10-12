from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ParamSchema:
    name: str
    type: str
    required: bool
    description: str
    schema: dict = field(default_factory=dict)


@dataclass
class FunctionMeta:
    callable_name: str
    description: str
    type: Literal["logic", "action"]
    params: list[ParamSchema]
    return_type: str
    source_path: str
    func_name: str
    ontology_id: str | int | None
    checksum: str


@dataclass
class ExecContext:
    call_stack: list[str] = field(default_factory=list)
    max_depth: int = 10
    timeout_sec: int = 30
    total_timeout_sec: int = 120
    ontology_id: str | int | None = None
    _chain_start: float | None = None
    version_id: str | None = None
    entity_ids: frozenset[str] | None = None
    function_ids: frozenset[str] | None = None
    user: Any = None
    action_mode: Literal["read", "simulation", "confirm", "execute"] = "read"
    allowed_tools: frozenset[str] | None = None
    committed_writes: list[dict] = field(default_factory=list)
    active_write: dict | None = None

    def check_entity(self, entity_id):
        if self.entity_ids is not None and entity_id not in self.entity_ids:
            raise PermissionError("对象不在当前授权范围内")

    def failure_outcome(self, error):
        outcome = getattr(error, "outcome", None)
        if outcome in {"unknown", "committed_unrecorded"}:
            return outcome
        if self.active_write is not None:
            return "unknown"
        return "partial_committed" if self.committed_writes else outcome


class FunctionWriteRequested(BaseException):
    """Stop before a write; script exception handlers cannot turn a preview into a write."""
    def __init__(self, request):
        self.request = request


@dataclass
class ExecResult:
    success: bool
    result: Any
    error: str | None
    execution_ms: int
    call_trace: list[str]
    outcome: str | None = None
    requested_write: dict | None = None
    committed_writes: list[dict] = field(default_factory=list)
