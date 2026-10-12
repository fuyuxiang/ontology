from string import Template
import httpx
from .base import BaseActionExecutor, ExecutionResult
from .http_receipt import classify_receipt


def _render(value, params):
    if isinstance(value, str):
        if value.startswith('$') and value[1:] in params:
            return params[value[1:]]
        return Template(value).substitute(params)
    if isinstance(value, dict):
        return {key: _render(item, params) for key, item in value.items()}
    if isinstance(value, list):
        return [_render(item, params) for item in value]
    return value


class ApiCallExecutor(BaseActionExecutor):
    async def execute(self, type_config, params, dry_run=False):
        try:
            url = Template(type_config.get('url', '')).substitute(params)
            method = type_config.get('method', 'GET').upper()
            headers = _render(type_config.get('headers', {}), params)
            body = _render(type_config.get('body', {}), params)
            timeout = float(type_config.get('timeout_seconds', 30))
            if not 0.05 <= timeout <= 120:
                return ExecutionResult(False, 'API timeout_seconds 必须在 0.05~120 秒范围内')
            if method not in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'} or not url.startswith(('http://', 'https://')):
                return ExecutionResult(False, 'API URL 或请求方法无效')
            if dry_run:
                return ExecutionResult(True, f'[Dry Run] Would {method} {url}', {'url': url, 'method': method, 'body': body})
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, headers=headers, json=body if body else None)
            try:
                response_body = response.json()
            except ValueError:
                response_body = response.text
            business_failure, uncertain = classify_receipt(response.status_code, response_body)
            success = response.is_success and not business_failure and not uncertain
            message = f'{method} {url} -> {response.status_code}'
            if uncertain:message += '，回执未确认，请核查源数据；禁止自动重试'
            return ExecutionResult(success, message,
                {'status_code': response.status_code, 'body': response_body,
                 'outcome': 'unknown' if uncertain else 'committed' if success else 'failed'})
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            return ExecutionResult(False, f'外部调用结果未知，请核对后重试: {exc}', {'outcome': 'unknown', 'error': str(exc)})
        except Exception as exc:
            return ExecutionResult(False, f'API 请求失败: {exc}', {'outcome': 'failed', 'error': str(exc)})
    @classmethod
    def get_config_schema(cls):
        return {'url': {'type':'string','required':True,'description':'请求 URL，支持 $param 占位符'},
                'method': {'type':'string','required':True,'enum':['GET','POST','PUT','PATCH','DELETE']},
                'headers': {'type':'object','required':False,'description':'请求头'},
                'body': {'type':'object','required':False,'description':'请求体模板，支持 $param 占位符'},
                'timeout_seconds': {'type':'number','required':False,'description':'请求超时秒数，0.05~120，默认 30'}}
    @classmethod
    def get_label(cls): return '调用 API'
    @classmethod
    def get_description(cls): return '发送 HTTP 请求到指定 URL'
