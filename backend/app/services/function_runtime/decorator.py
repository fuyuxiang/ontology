from __future__ import annotations

from typing import Literal


def Function(
    name: str,
    description: str,
    type: Literal["logic", "action"],
    params: list[dict] | None = None,
    return_type: str = "object",
):
    """Decorator that attaches function metadata for the runtime registry."""
    def wrapper(func):
        func._function_meta = {
            "name": name,
            "description": description,
            "type": type,
            "params": params,
            "return_type": return_type,
        }
        return func
    return wrapper
