from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .config import ConfigError, LLMConfig


def call_llm(config: LLMConfig, messages: list[dict[str, str]]) -> str:
    api_key = os.getenv(config.api_key_env)
    if not api_key:
        raise ConfigError(f"Environment variable {config.api_key_env} is required for LLM access")

    payload: dict[str, object] = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
    }
    if config.use_json_mode:
        payload["response_format"] = {"type": "json_object"}

    request = urllib.request.Request(
        url=f"{config.base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **config.extra_headers,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"LLM response missing choices: {body}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_chunks = [item.get("text", "") for item in content if isinstance(item, dict)]
        merged = "".join(text_chunks).strip()
        if merged:
            return merged
    raise RuntimeError(f"LLM response missing usable message content: {body}")
