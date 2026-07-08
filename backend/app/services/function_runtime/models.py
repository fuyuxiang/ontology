from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ParamSchema:
    name: str
    type: str
    required: bool
    description: str


@dataclass
class FunctionMeta:
    callable_name: str
    description: str
    type: Literal["logic", "action"]
    params: list[ParamSchema]
    return_type: str
    source_path: str
    func_name: str
    ontology_id: int
    checksum: str


@dataclass
class ExecContext:
    call_stack: list[str] = field(default_factory=list)
    max_depth: int = 10
    timeout_sec: int = 30
    total_timeout_sec: int = 120
    ontology_id: int | None = None


@dataclass
class ExecResult:
    success: bool
    result: Any
    error: str | None
    execution_ms: int
    call_trace: list[str]
