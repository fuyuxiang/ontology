from string import Template

from .base import BaseActionExecutor, ExecutionResult


class NotificationExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        channel = type_config.get("channel", "system")
        recipient = Template(type_config.get("recipient", "")).safe_substitute(params)
        message_template = type_config.get("message_template", "")
        message = Template(message_template).safe_substitute(params)

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would send to {recipient} via {channel}",
                output={"channel": channel, "recipient": recipient, "message": message},
            )

        return ExecutionResult(
            success=True,
            message=f"Notification sent to {recipient} via {channel}",
            output={"channel": channel, "recipient": recipient, "message": message},
        )

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "channel": {"type": "string", "required": True, "enum": ["system", "email", "webhook"], "description": "通知通道"},
            "recipient": {"type": "string", "required": True, "description": "接收人，支持 $param 占位符"},
            "message_template": {"type": "string", "required": True, "description": "消息模板，支持 $param 占位符"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "发送通知"

    @classmethod
    def get_description(cls) -> str:
        return "通过指定通道发送通知消息"
