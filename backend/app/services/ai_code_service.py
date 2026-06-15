import json
import logging
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy.orm import Session

from app.models.ai_code_conversation import AiCodeConversation
from app.models.entity import OntologyEntity, EntityAttribute
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
    def __init__(self, db: Session):
        self.db = db

    def generate_stream(self, target_type: str, target_id: str, message: str, extra_entity_ids: list[str]) -> Generator[str, None, str]:
        context = self._build_context(target_type, target_id, extra_entity_ids)
        conversation = self._get_or_create_conversation(target_type, target_id, extra_entity_ids)

        history = conversation.messages[-MAX_HISTORY_ROUNDS * 2:] if conversation.messages else []
        history.append({"role": "user", "content": message, "timestamp": datetime.now(timezone.utc).isoformat()})

        llm_messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}]
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

        history.append({"role": "assistant", "content": full_response, "timestamp": datetime.now(timezone.utc).isoformat()})
        conversation.messages = history
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return full_response

    def get_conversation(self, target_type: str, target_id: str) -> AiCodeConversation | None:
        return self.db.query(AiCodeConversation).filter(
            AiCodeConversation.target_type == target_type,
            AiCodeConversation.target_id == target_id,
        ).first()

    def _get_or_create_conversation(self, target_type: str, target_id: str, extra_entity_ids: list[str]) -> AiCodeConversation:
        conv = self.get_conversation(target_type, target_id)
        if not conv:
            conv = AiCodeConversation(
                target_type=target_type,
                target_id=target_id,
                messages=[],
                context_entity_ids=extra_entity_ids,
            )
            self.db.add(conv)
            self.db.flush()
        return conv

    def _build_context(self, target_type: str, target_id: str, extra_entity_ids: list[str]) -> str:
        if target_type == "function":
            func = self.db.query(OntologyFunction).get(target_id)
            if not func:
                return ""
            return self._build_function_context(func, extra_entity_ids)
        else:
            from app.repositories.action_repo import ActionRepository
            repo = ActionRepository(self.db)
            action = repo.get(target_id)
            if not action:
                return ""
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
