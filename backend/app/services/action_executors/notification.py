"""Send notifications with durable receipts and explicit delivery outcomes."""
import hashlib
import hmac
import json
import smtplib
import asyncio
from email.message import EmailMessage
from string import Template
from uuid import uuid4

import httpx

from .base import BaseActionExecutor, ExecutionResult
from .http_receipt import classify_receipt


class NotificationExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        channel = type_config.get("channel", "system")
        try:
            recipient = Template(type_config.get("recipient", "")).substitute(params)
            message = Template(type_config.get("message_template", "")).substitute(params)
            timeout = float(type_config.get("timeout_seconds", 15))
            if not 0.05 <= timeout <= 120:
                return ExecutionResult(False, "通知 timeout_seconds 必须在 0.05~120 秒范围内")
        except (ValueError, KeyError) as exc:
            return ExecutionResult(False, f"通知模板参数错误: {exc}")
        output = {"channel": channel, "recipient": recipient, "message": message}
        if dry_run:
            return ExecutionResult(True, f"[Dry Run] Would send to {recipient} via {channel}", output)
        if not recipient or not message:
            return ExecutionResult(False, "通知接收人和消息不能为空", output)
        from app.database import SessionLocal
        from app.api.v1.system_config import _get_config_value
        from app.models.user import User
        from app.services.audit import write_audit
        db = self.db or SessionLocal()
        sent = False
        receipt_id = str(uuid4())
        def config(key, default=""):
            value = _get_config_value(db, f"notification.{key}")
            return value if value is not None else default
        try:
            if channel == "system":
                users = db.query(User).filter((User.id == recipient) | (User.username == recipient) | (User.email == recipient), User.is_active.is_(True)).all()
                if len(users) != 1:
                    return ExecutionResult(False, "系统通知接收人不存在或有歧义", output)
                output["recipient_user_id"] = users[0].id
            elif channel == "webhook":
                url = type_config.get("webhook_url") or config("webhook_url")
                if not url:
                    return ExecutionResult(False, "未配置通知 webhook_url", output)
                payload = {"recipient": recipient, "message": message, "receipt_id": receipt_id}
                body = json.dumps(payload, ensure_ascii=False).encode()
                headers = {"Content-Type": "application/json"}
                secret = config("webhook_secret")
                if secret:
                    headers["X-Webhook-Signature"] = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, content=body, headers=headers)
                try:
                    receipt_body = response.json()
                except ValueError:
                    receipt_body = None
                business_failure, uncertain = classify_receipt(response.status_code, receipt_body)
                if uncertain:
                    return ExecutionResult(False, "通知回执未确认，请核查外部接收记录；禁止自动重试",
                        {**output, "receipt_id": receipt_id, "status_code": response.status_code, "body": receipt_body, "outcome": "unknown"})
                if not response.is_success or business_failure:
                    return ExecutionResult(False, f"Webhook 拒绝通知: HTTP {response.status_code}", {**output, "status_code": response.status_code})
                output["status_code"] = response.status_code
                output["external_receipt"] = response.headers.get("X-Receipt-ID")
                sent = True
            elif channel == "email":
                host, username = config("smtp_host"), config("smtp_username")
                if not host or not username:
                    return ExecutionResult(False, "未配置 SMTP 服务器和发件人", output)
                port = int(config("smtp_port", "465"))
                encryption = config("smtp_encryption", "ssl")
                email = EmailMessage()
                email["From"] = username
                email["To"] = recipient
                email["Subject"] = type_config.get("subject", "本体平台通知")
                email["Message-ID"] = f"<{receipt_id}@ontology.local>"
                email.set_content(message)
                password = config("smtp_password")
                def send_email():
                    server_class = smtplib.SMTP_SSL if encryption == "ssl" else smtplib.SMTP
                    with server_class(host, port, timeout=timeout) as server:
                        if encryption == "tls":
                            server.starttls()
                        if password:
                            server.login(username, password)
                        return server.send_message(email)
                refused = await asyncio.to_thread(send_email)
                if refused:
                    return ExecutionResult(False, "SMTP 部分接收人被拒绝，须核对已发送回执，禁止自动重发",
                                           {**output, "outcome": "unknown", "refused_recipients": list(refused)})
                sent = True
            else:
                return ExecutionResult(False, f"未知通知通道: {channel}", output)
            write_audit(db, user_id=output.get("recipient_user_id"), user_name=recipient,
                        action="notify", target_type="notification", target_id=receipt_id,
                        target_name=channel, details=json.dumps(output, ensure_ascii=False), status="success")
            db.commit()
            return ExecutionResult(True, "通知已提交，回执已持久化", {**output, "receipt_id": receipt_id, "outcome": "committed"})
        except (httpx.TimeoutException, httpx.TransportError, smtplib.SMTPServerDisconnected, TimeoutError) as exc:
            return ExecutionResult(False, f"通知结果未知，请核对回执后重试: {exc}", {**output, "receipt_id": receipt_id, "outcome": "unknown"})
        except Exception as exc:
            db.rollback()
            return ExecutionResult(False, f"通知发送失败: {exc}", {**output, "receipt_id": receipt_id, "outcome": "unknown" if sent else "failed"})
        finally:
            if self.db is None:
                db.close()

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "channel": {"type": "string", "required": True, "enum": ["system", "email", "webhook"], "description": "通知通道"},
            "recipient": {"type": "string", "required": True, "description": "接收人，支持 $param 占位符"},
            "message_template": {"type": "string", "required": True, "description": "消息模板，支持 $param 占位符"},
            "timeout_seconds": {"type": "number", "required": False, "description": "发送超时秒数，0.05~120，默认 15"},
        }

    @classmethod
    def get_label(cls):
        return "发送通知"

    @classmethod
    def get_description(cls):
        return "通过指定通道发送通知消息并保存回执"
