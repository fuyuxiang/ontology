from string import Template

import httpx

from .base import BaseActionExecutor, ExecutionResult


class ApiCallExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        url = Template(type_config.get("url", "")).safe_substitute(params)
        method = type_config.get("method", "GET").upper()
        headers = type_config.get("headers", {})
        body_template = type_config.get("body", {})

        body = {}
        if body_template:
            body = {k: Template(str(v)).safe_substitute(params) for k, v in body_template.items()}

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would {method} {url}",
                output={"url": url, "method": method, "body": body},
            )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, url, headers=headers, json=body if body else None)
            content_type = response.headers.get("content-type", "")
            resp_body = response.json() if "application/json" in content_type else response.text
            return ExecutionResult(
                success=response.is_success,
                message=f"{method} {url} -> {response.status_code}",
                output={"status_code": response.status_code, "body": resp_body},
            )

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "url": {"type": "string", "required": True, "description": "请求 URL，支持 $param 占位符"},
            "method": {"type": "string", "required": True, "enum": ["GET", "POST", "PUT", "DELETE"]},
            "headers": {"type": "object", "required": False, "description": "请求头"},
            "body": {"type": "object", "required": False, "description": "请求体模板，支持 $param 占位符"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "调用 API"

    @classmethod
    def get_description(cls) -> str:
        return "发送 HTTP 请求到指定 URL"
