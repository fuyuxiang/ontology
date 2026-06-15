from .base import BaseActionExecutor, ExecutionResult


class SqlExecExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        connection_id = type_config.get("connection_id")
        sql_template = type_config.get("sql", "")

        if not connection_id:
            return ExecutionResult(success=False, message="未指定 connection_id", output={})

        sql_params = {}
        for key, value in params.items():
            placeholder = f"${key}"
            if placeholder in sql_template:
                sql_template = sql_template.replace(placeholder, f":{key}")
                sql_params[key] = value

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would execute SQL on connection {connection_id}",
                output={"sql": sql_template, "params": sql_params, "connection_id": connection_id},
            )

        from app.database import get_db
        from app.services.data_plane.execute_service import ExecuteService

        try:
            db = next(get_db())
            svc = ExecuteService(db)
            result = svc.execute_on_connection(
                connection_id=connection_id,
                sql=sql_template,
                params=sql_params,
                purpose="action_sql_exec",
                write=True,
                timeout_ms=30000,
            )
            return ExecutionResult(
                success=True,
                message=f"SQL 执行成功，影响 {result.row_count} 行",
                output={"rows_affected": result.row_count, "columns": result.columns, "data": result.rows[:100]},
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"SQL 执行失败: {str(e)}",
                output={"error": str(e)},
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
