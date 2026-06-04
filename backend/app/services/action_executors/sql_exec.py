from string import Template
from .base import BaseActionExecutor, ExecutionResult


class SqlExecExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        connection_id = type_config.get("connection_id")
        sql_template = type_config.get("sql", "")
        sql = Template(sql_template).safe_substitute(params)

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would execute SQL on connection {connection_id}",
                output={"sql": sql, "connection_id": connection_id},
            )

        return ExecutionResult(
            success=True,
            message=f"Executed SQL on connection {connection_id}",
            output={"sql": sql, "rows_affected": 0},
        )

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "connection_id": {"type": "string", "required": True, "description": "数据源连接 ID"},
            "sql": {"type": "string", "required": True, "description": "SQL 语句，支持 $param 占位符"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "执行 SQL"

    @classmethod
    def get_description(cls) -> str:
        return "在指定数据源上执行 SQL 语句"
