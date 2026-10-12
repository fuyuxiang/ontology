import logging
from collections.abc import Generator
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.ai_code_conversation import AiCodeConversation
from app.models.entity import OntologyEntity
from app.models.function import OntologyFunction
from app.services.llm_resolver import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个 Python 代码生成助手，为本体平台的函数/行动生成执行逻辑。

规则：
- 生成纯 Python 代码，不要 markdown 包裹
- 通过 params 字典获取输入参数，结果写入 result 变量
- 只允许使用以下模块：math, datetime, json, re, decimal, collections
- 不允许文件操作、网络请求、系统调用
- 代码简洁，必要时加简短中文注释
- 如果用户描述模糊，先反问澄清而不是猜测生成"""

MAX_HISTORY_ROUNDS = 10


class AiCodeService:
    def __init__(self, db: Session, owner_id: str | None = None):
        self.db = db
        self.owner_id = owner_id

    def generate_stream(self, target_type: str, target_id: str, message: str, extra_entity_ids: list[str], execution_mode: str | None = None) -> Generator[str, None, str]:
        mode = self._execution_mode(target_type, target_id, execution_mode)
        context = self._build_context(target_type, target_id, extra_entity_ids)
        if mode == "sql":
            context += "\n" + self._build_sql_context(target_type, target_id, extra_entity_ids)
        conversation = self._get_or_create_conversation(target_type, target_id, extra_entity_ids)

        history = [dict(item) for item in (conversation.messages or []) if item.get("execution_mode", mode) == mode][-MAX_HISTORY_ROUNDS * 2:]
        history.append({"role": "user", "content": message, "timestamp": datetime.now(UTC).isoformat(), "execution_mode": mode})

        llm_messages = [{"role": "system", "content": self._prompt_for_mode(mode) + "\n\n" + context}]
        for msg in history:
            llm_messages.append({"role": msg["role"], "content": msg["content"]})

        client = get_llm_client(self.db, scene="general")
        full_response = ""

        stream = client.chat.completions.create(
            model=client._model_name if hasattr(client, "_model_name") else "gpt-4",
            messages=llm_messages,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token

        if not full_response.strip():
            raise ValueError("模型未生成有效代码，请重试")
        history.append({"role": "assistant", "content": full_response, "timestamp": datetime.now(UTC).isoformat(), "execution_mode": mode})
        conversation.messages = history
        conversation.updated_at = datetime.now(UTC)
        self.db.commit()

        return full_response

    def get_conversation(self, target_type: str, target_id: str) -> AiCodeConversation | None:
        return self.db.query(AiCodeConversation).filter(
            AiCodeConversation.target_type == target_type,
            AiCodeConversation.target_id == target_id,
            AiCodeConversation.owner_id == self.owner_id,
        ).first()

    def _get_or_create_conversation(self, target_type: str, target_id: str, extra_entity_ids: list[str]) -> AiCodeConversation:
        conv = self.get_conversation(target_type, target_id)
        if not conv:
            conv = AiCodeConversation(
                owner_id=self.owner_id,
                target_type=target_type,
                target_id=target_id,
                messages=[],
                context_entity_ids=extra_entity_ids,
            )
            self.db.add(conv)
            self.db.flush()
        return conv

    def _execution_mode(self, target_type, target_id, requested):
        if target_type == "action":
            from app.models.action import EntityAction
            action = self.db.get(EntityAction, target_id) if not target_id.startswith("tmp_") else None
            if action and action.action_type != "custom_script":
                raise ValueError("AI Python 逻辑仅适用于自定义脚本行动；其他行动请编辑执行配置")
            if requested not in {None, "custom_script"}:
                raise ValueError("行动代码必须使用 custom_script 模式")
            return "custom_script"
        function = self.db.get(OntologyFunction, target_id) if not target_id.startswith("tmp_") else None
        mode = requested or (function.logic_type if function else "python")
        if mode not in {"expression", "sql", "python"}:
            raise ValueError("函数逻辑模式无效")
        return mode

    @staticmethod
    def _prompt_for_mode(mode):
        contract = {
            "expression": "仅生成一个可 eval 的 Python 表达式。通过 params[参数名] 读取输入；不允许赋值、def、import、result变量或markdown。可用纯函数 abs/max/min/round/len/int/float/str/bool。",
            "sql": "仅生成一条只读 SELECT SQL，不要Python或markdown。参数必须使用 :参数名 命名占位符，使用上下文真实资产/字段，不允许DDL/DML、多语句或拼接参数。",
            "python": "生成可放入函数执行体的纯Python语句。通过 params 字典读取输入，结果写入 result 变量；不要 def、@Function或markdown。允许math/datetime/json/re/decimal/collections；禁止文件、网络、系统调用。",
            "custom_script": "生成可放入行动执行体的纯Python语句。通过 params 字典读取输入，必须把输出写入 result 字典；不要 def、@Function或markdown。允许math/datetime/json/re/decimal/collections；禁止文件、网络、系统调用。",
        }
        return "你为本体平台生成执行逻辑。当前执行模式：" + mode + "。\n" + contract[mode] + "\n语义不充分时先说明缺少的目标与输入，不能编造业务规则。"

    def _build_sql_context(self, target_type, target_id, extra_entity_ids):
        from app.models.object_binding import ObjectBinding
        from app.models.asset import Asset
        function = self.db.get(OntologyFunction, target_id) if target_type == "function" else None
        ids = set(extra_entity_ids)
        if function and function.entity_id:
            ids.add(function.entity_id)
        rows = []
        for binding in self.db.query(ObjectBinding).filter(ObjectBinding.object_type_id.in_(ids), ObjectBinding.status == "active").all():
            asset = self.db.get(Asset, binding.asset_id)
            if asset:
                rows.append({"table":(asset.locator or {}).get("table"), "schema":asset.schema_snapshot or [], "field_mappings":binding.field_mappings or []})
        import json
        return "SQL仅可查询已绑定资产（未提供凭据）：" + json.dumps(rows,ensure_ascii=False,default=str)

    def _build_context(self, target_type: str, target_id: str, extra_entity_ids: list[str]) -> str:
        if target_id.startswith("tmp_"):
            return self._build_entity_only_context(extra_entity_ids)
        if target_type == "function":
            func = self.db.query(OntologyFunction).get(target_id)
            if not func:
                return self._build_entity_only_context(extra_entity_ids)
            return self._build_function_context(func, extra_entity_ids)
        else:
            from app.repositories.action_repo import ActionRepository
            repo = ActionRepository(self.db)
            action = repo.get_by_id(target_id)
            if not action:
                return self._build_entity_only_context(extra_entity_ids)
            return self._build_action_context(action, extra_entity_ids)

    def _build_function_context(self, func: OntologyFunction, extra_entity_ids: list[str]) -> str:
        lines = [
            "## 当前函数信息",
            f"名称：{func.name}",
            f"描述：{func.description}",
            f"返回类型：{func.return_type}",
            f"逻辑类型：{func.logic_type}",
            "输入参数：",
        ]
        entity_ids = set()
        if func.entity_id:
            entity_ids.add(func.entity_id)

        if func.input_schema:
            for p in func.input_schema:
                line = f"  - {p.get('name')}: {p.get('type', 'string')}"
                if p.get("required"):
                    line += " (必填)"
                if p.get("description"):
                    line += f" — {p['description']}"
                lines.append(line)
                if p.get("entity_id"):
                    entity_ids.add(p["entity_id"])

        for eid in extra_entity_ids:
            entity_ids.add(eid)

        if entity_ids:
            lines.append("\n## 本体上下文")
            seen = set()
            for eid in entity_ids:
                if eid in seen:
                    continue
                seen.add(eid)
                entity = self._load_entity(eid)
                if entity:
                    lines.append(f"\n### 实体：{entity.name_cn}({entity.name})")
                    if entity.description:
                        lines.append(f"描述：{entity.description}")
                    lines.append("属性：")
                    for attr in entity.attributes:
                        lines.append(f"  - {attr.name}: {attr.type} — {attr.description or ''}")

        return "\n".join(lines)

    def _build_entity_only_context(self, extra_entity_ids: list[str]) -> str:
        if not extra_entity_ids:
            return ""
        lines = ["## 关联实体信息"]
        for eid in extra_entity_ids:
            entity = self._load_entity(eid)
            if entity:
                lines.append(f"\n### 实体：{entity.name_cn}({entity.name})")
                if entity.description:
                    lines.append(f"描述：{entity.description}")
                lines.append("属性：")
                for attr in entity.attributes:
                    lines.append(f"  - {attr.name}: {attr.type} — {attr.description or ''}")
        return "\n".join(lines)

    def _build_action_context(self, action, extra_entity_ids: list[str]) -> str:
        lines = [
            "## 当前行动信息",
            f"名称：{action.name}",
            f"描述：{action.description or ''}",
            f"类型：{action.action_type}",
            "参数：",
        ]
        entity_ids = set()
        if action.entity_id:
            entity_ids.add(action.entity_id)

        if action.parameters_json:
            for p in action.parameters_json:
                name = p.get("name", "") if isinstance(p, dict) else p.name
                ptype = p.get("type", "string") if isinstance(p, dict) else p.type
                desc = p.get("description", "") if isinstance(p, dict) else (p.description or "")
                lines.append(f"  - {name}: {ptype} — {desc}")

        for eid in extra_entity_ids:
            entity_ids.add(eid)

        if entity_ids:
            lines.append("\n## 本体上下文")
            seen = set()
            for eid in entity_ids:
                if eid in seen:
                    continue
                seen.add(eid)
                entity = self._load_entity(eid)
                if entity:
                    lines.append(f"\n### 实体：{entity.name_cn}({entity.name})")
                    if entity.description:
                        lines.append(f"描述：{entity.description}")
                    lines.append("属性：")
                    for attr in entity.attributes:
                        lines.append(f"  - {attr.name}: {attr.type} — {attr.description or ''}")

        return "\n".join(lines)

    def _load_entity(self, entity_id: str) -> OntologyEntity | None:
        return self.db.query(OntologyEntity).filter(OntologyEntity.id == entity_id).first()
