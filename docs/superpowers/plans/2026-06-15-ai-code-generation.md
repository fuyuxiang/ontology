# AI 代码生成器实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为函数管理和行动管理模块增加自然语言→Python 代码生成能力，包含本体上下文注入、SSE 流式生成、安全校验和函数测试。

**Architecture:** 后端新增 ai_code 模块（model + service + API router），复用现有 `llm_resolver` 获取 LLM 客户端，复用 `copilot.py` 的 SSE 模式。前端在 `FunctionBuilderDrawer` 中集成 AI 对话抽屉面板。安全层通过 AST 白名单静态分析实现。

**Tech Stack:** Python/FastAPI (后端), SQLAlchemy (ORM), OpenAI SDK (LLM), Vue 3 + TypeScript (前端)

---

## 文件结构

### 后端新增文件
- `backend/app/models/ai_code_conversation.py` — 对话历史数据模型
- `backend/app/schemas/ai_code.py` — 请求/响应 Schema
- `backend/app/services/ai_code_service.py` — 核心服务：上下文组装 + LLM 调用 + 流式生成
- `backend/app/services/code_validator.py` — AST 静态安全分析
- `backend/app/api/v1/ai_code.py` — API 路由
- `backend/tests/test_code_validator.py` — 安全分析测试
- `backend/tests/test_ai_code_service.py` — 服务层测试

### 前端新增文件
- `frontend/src/api/aiCode.ts` — AI 代码生成 API 层
- `frontend/src/components/logic/AiCodePanel.vue` — AI 对话抽屉面板

### 前端修改文件
- `frontend/src/components/logic/FunctionBuilderDrawer.vue` — 集成 AI 生成按钮

---

## Task 1: 代码安全校验器 (code_validator)

**Files:**
- Create: `backend/app/services/code_validator.py`
- Test: `backend/tests/test_code_validator.py`

- [ ] **Step 1: 编写校验器测试**

```python
# backend/tests/test_code_validator.py
import pytest
from app.services.code_validator import validate_code, ValidationResult


class TestCodeValidator:
    def test_safe_code_passes(self):
        code = "result = params['amount'] * 1.1"
        r = validate_code(code)
        assert r.safe is True
        assert r.violations == []

    def test_allowed_import_passes(self):
        code = "import math\nresult = math.sqrt(params['x'])"
        r = validate_code(code)
        assert r.safe is True

    def test_forbidden_import_os(self):
        code = "import os\nresult = os.listdir('/')"
        r = validate_code(code)
        assert r.safe is False
        assert any("os" in v.reason for v in r.violations)

    def test_forbidden_import_subprocess(self):
        code = "import subprocess\nresult = subprocess.run(['ls'])"
        r = validate_code(code)
        assert r.safe is False

    def test_forbidden_open(self):
        code = "f = open('/etc/passwd')\nresult = f.read()"
        r = validate_code(code)
        assert r.safe is False
        assert any("open" in v.reason for v in r.violations)

    def test_forbidden_eval(self):
        code = "result = eval('1+1')"
        r = validate_code(code)
        assert r.safe is False

    def test_forbidden_exec(self):
        code = "exec('print(1)')\nresult = None"
        r = validate_code(code)
        assert r.safe is False

    def test_forbidden_dunder_import(self):
        code = "os = __import__('os')\nresult = os.getcwd()"
        r = validate_code(code)
        assert r.safe is False

    def test_syntax_error(self):
        code = "def foo(\nresult = 1"
        r = validate_code(code)
        assert r.safe is False
        assert any("syntax" in v.reason.lower() for v in r.violations)

    def test_allowed_multiple_imports(self):
        code = "import math\nimport json\nimport re\nresult = math.pi"
        r = validate_code(code)
        assert r.safe is True

    def test_from_import_forbidden(self):
        code = "from os.path import join\nresult = join('a', 'b')"
        r = validate_code(code)
        assert r.safe is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_code_validator.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现校验器**

```python
# backend/app/services/code_validator.py
import ast
from dataclasses import dataclass, field


ALLOWED_MODULES = {"math", "datetime", "json", "re", "decimal", "collections"}
FORBIDDEN_CALLS = {"open", "eval", "exec", "__import__", "compile", "globals", "locals", "getattr", "setattr", "delattr"}


@dataclass
class Violation:
    line: int
    reason: str


@dataclass
class ValidationResult:
    safe: bool
    violations: list[Violation] = field(default_factory=list)


def validate_code(code: str) -> ValidationResult:
    violations: list[Violation] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ValidationResult(safe=False, violations=[Violation(line=e.lineno or 1, reason=f"Syntax error: {e.msg}")])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".")[0]
                if module_root not in ALLOWED_MODULES:
                    violations.append(Violation(line=node.lineno, reason=f"Forbidden import: {alias.name}"))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split(".")[0]
                if module_root not in ALLOWED_MODULES:
                    violations.append(Violation(line=node.lineno, reason=f"Forbidden import: {node.module}"))

        elif isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name in FORBIDDEN_CALLS:
                violations.append(Violation(line=node.lineno, reason=f"Forbidden call: {func_name}"))

    return ValidationResult(safe=len(violations) == 0, violations=violations)


def _get_call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_code_validator.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/code_validator.py backend/tests/test_code_validator.py
git commit -m "feat: add AST-based code validator with whitelist module checking"
```

---

## Task 2: 对话历史数据模型

**Files:**
- Create: `backend/app/models/ai_code_conversation.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建模型文件**

```python
# backend/app/models/ai_code_conversation.py
from datetime import datetime

from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class AiCodeConversation(Base):
    __tablename__ = "ai_code_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    context_entity_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: 在 models/__init__.py 中注册**

在 `backend/app/models/__init__.py` 中添加 import：

```python
from app.models.ai_code_conversation import AiCodeConversation  # noqa: F401
```

- [ ] **Step 3: 验证模型可被 import**

Run: `cd backend && python -c "from app.models.ai_code_conversation import AiCodeConversation; print(AiCodeConversation.__tablename__)"`
Expected: `ai_code_conversations`

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/ai_code_conversation.py backend/app/models/__init__.py
git commit -m "feat: add AiCodeConversation model for persisting AI code generation history"
```

---

## Task 3: Schema 定义

**Files:**
- Create: `backend/app/schemas/ai_code.py`

- [ ] **Step 1: 创建 Schema 文件**

```python
# backend/app/schemas/ai_code.py
from pydantic import BaseModel
from datetime import datetime


class AiCodeGenerateRequest(BaseModel):
    target_type: str  # "function" | "action"
    target_id: str
    message: str
    extra_entity_ids: list[str] = []


class AiCodeValidateRequest(BaseModel):
    code: str


class ViolationOut(BaseModel):
    line: int
    reason: str


class AiCodeValidateResponse(BaseModel):
    safe: bool
    violations: list[ViolationOut] = []


class ConversationMessageOut(BaseModel):
    role: str
    content: str
    timestamp: str


class ConversationOut(BaseModel):
    id: str
    target_type: str
    target_id: str
    messages: list[ConversationMessageOut]
    context_entity_ids: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 验证 Schema 可被 import**

Run: `cd backend && python -c "from app.schemas.ai_code import AiCodeGenerateRequest; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add backend/app/schemas/ai_code.py
git commit -m "feat: add Pydantic schemas for AI code generation API"
```

---

## Task 4: AI 代码生成服务

**Files:**
- Create: `backend/app/services/ai_code_service.py`
- Test: `backend/tests/test_ai_code_service.py`

- [ ] **Step 1: 编写上下文组装测试**

```python
# backend/tests/test_ai_code_service.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.ai_code_service import AiCodeService


class TestContextBuilding:
    def setup_method(self):
        self.db = MagicMock()
        self.service = AiCodeService(self.db)

    def test_build_context_for_function(self):
        mock_func = MagicMock()
        mock_func.name = "calculate_total"
        mock_func.description = "计算总金额"
        mock_func.return_type = "number"
        mock_func.input_schema = [
            {"name": "customer_id", "type": "string", "required": True, "description": "客户ID", "entity_id": "ent-1"}
        ]
        mock_func.entity_id = "ent-2"
        mock_func.logic_type = "python"

        mock_entity = MagicMock()
        mock_entity.name = "Customer"
        mock_entity.name_cn = "客户"
        mock_entity.description = "客户实体"
        mock_attr = MagicMock()
        mock_attr.name = "total_amount"
        mock_attr.type = "number"
        mock_attr.description = "消费总额"
        mock_entity.attributes = [mock_attr]

        with patch.object(self.service, "_load_entity", return_value=mock_entity):
            context = self.service._build_function_context(mock_func, extra_entity_ids=[])

        assert "calculate_total" in context
        assert "customer_id" in context
        assert "Customer" in context

    def test_build_context_deduplicates_entities(self):
        mock_func = MagicMock()
        mock_func.name = "test"
        mock_func.description = ""
        mock_func.return_type = "string"
        mock_func.input_schema = [
            {"name": "id", "type": "string", "entity_id": "ent-1"}
        ]
        mock_func.entity_id = "ent-1"
        mock_func.logic_type = "python"

        mock_entity = MagicMock()
        mock_entity.name = "Order"
        mock_entity.name_cn = "订单"
        mock_entity.description = ""
        mock_entity.attributes = []

        with patch.object(self.service, "_load_entity", return_value=mock_entity) as mock_load:
            self.service._build_function_context(mock_func, extra_entity_ids=["ent-1"])

        mock_load.assert_called_once_with("ent-1")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_ai_code_service.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现服务**

```python
# backend/app/services/ai_code_service.py
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_ai_code_service.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/ai_code_service.py backend/tests/test_ai_code_service.py
git commit -m "feat: add AI code generation service with ontology context injection"
```

---

## Task 5: API 路由

**Files:**
- Create: `backend/app/api/v1/ai_code.py`
- Modify: `backend/app/main.py` (注册路由)

- [ ] **Step 1: 创建 API 路由**

```python
# backend/app/api/v1/ai_code.py
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai_code import (
    AiCodeGenerateRequest,
    AiCodeValidateRequest,
    AiCodeValidateResponse,
    ViolationOut,
    ConversationOut,
    ConversationMessageOut,
)
from app.services.ai_code_service import AiCodeService
from app.services.code_validator import validate_code

router = APIRouter(prefix="/ai-code", tags=["ai-code"])


@router.post("/generate")
def generate_code(req: AiCodeGenerateRequest, db: Session = Depends(get_db)):
    service = AiCodeService(db)

    def event_stream():
        try:
            full_code = ""
            for token in service.generate_stream(
                target_type=req.target_type,
                target_id=req.target_id,
                message=req.message,
                extra_entity_ids=req.extra_entity_ids,
            ):
                full_code += token
                data = json.dumps({"event": "chunk", "content": token}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            conv = service.get_conversation(req.target_type, req.target_id)
            done_data = json.dumps({
                "event": "done",
                "full_code": full_code,
                "conversation_id": conv.id if conv else None,
            }, ensure_ascii=False)
            yield f"data: {done_data}\n\n"
        except Exception as e:
            error_data = json.dumps({"event": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations/{target_type}/{target_id}", response_model=ConversationOut | None)
def get_conversation(target_type: str, target_id: str, db: Session = Depends(get_db)):
    service = AiCodeService(db)
    conv = service.get_conversation(target_type, target_id)
    if not conv:
        return None
    return ConversationOut(
        id=conv.id,
        target_type=conv.target_type,
        target_id=conv.target_id,
        messages=[ConversationMessageOut(**m) for m in (conv.messages or [])],
        context_entity_ids=conv.context_entity_ids or [],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.post("/validate", response_model=AiCodeValidateResponse)
def validate_code_endpoint(req: AiCodeValidateRequest):
    result = validate_code(req.code)
    return AiCodeValidateResponse(
        safe=result.safe,
        violations=[ViolationOut(line=v.line, reason=v.reason) for v in result.violations],
    )
```

- [ ] **Step 2: 在 main.py 中注册路由**

在 `backend/app/main.py` 中找到路由注册区域，添加：

```python
from app.api.v1.ai_code import router as ai_code_router
app.include_router(ai_code_router, prefix="/api/v1")
```

- [ ] **Step 3: 验证服务启动**

Run: `cd backend && python -c "from app.api.v1.ai_code import router; print(f'Routes: {len(router.routes)}')"`
Expected: `Routes: 3`

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/v1/ai_code.py backend/app/main.py
git commit -m "feat: add AI code generation API routes (generate/validate/conversations)"
```

---

## Task 6: 前端 API 层

**Files:**
- Create: `frontend/src/api/aiCode.ts`

- [ ] **Step 1: 创建前端 API 文件**

```typescript
// frontend/src/api/aiCode.ts
import { get, post } from './client'

export interface AiCodeGenerateRequest {
  target_type: 'function' | 'action'
  target_id: string
  message: string
  extra_entity_ids?: string[]
}

export interface Violation {
  line: number
  reason: string
}

export interface ValidateResponse {
  safe: boolean
  violations: Violation[]
}

export interface ConversationMessage {
  role: string
  content: string
  timestamp: string
}

export interface Conversation {
  id: string
  target_type: string
  target_id: string
  messages: ConversationMessage[]
  context_entity_ids: string[]
  updated_at: string | null
}

export const aiCodeApi = {
  generateStream(req: AiCodeGenerateRequest): EventSource {
    const url = `/api/v1/ai-code/generate`
    const eventSource = new EventSource(url, { withCredentials: true })
    return eventSource
  },

  async generatePost(req: AiCodeGenerateRequest): Promise<Response> {
    const resp = await fetch('/api/v1/ai-code/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    return resp
  },

  getConversation(targetType: string, targetId: string) {
    return get<Conversation | null>(`/ai-code/conversations/${targetType}/${targetId}`)
  },

  validate(code: string) {
    return post<ValidateResponse>('/ai-code/validate', { code })
  },
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/aiCode.ts
git commit -m "feat: add frontend API layer for AI code generation"
```

---

## Task 7: AI 对话面板组件

**Files:**
- Create: `frontend/src/components/logic/AiCodePanel.vue`

- [ ] **Step 1: 创建 AiCodePanel 组件**

```vue
<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { aiCodeApi } from '../../api/aiCode'
import { entityApi } from '../../api/ontology'
import type { ConversationMessage } from '../../api/aiCode'
import type { EntityListItem } from '../../types'

const props = defineProps<{
  visible: boolean
  targetType: 'function' | 'action'
  targetId: string
  contextEntityIds: string[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'apply', code: string): void
}>()

const messages = ref<ConversationMessage[]>([])
const inputText = ref('')
const generating = ref(false)
const currentResponse = ref('')
const chatContainer = ref<HTMLElement | null>(null)
const entities = ref<EntityListItem[]>([])
const extraEntityIds = ref<string[]>([])

onMounted(async () => {
  entities.value = await entityApi.list()
  await loadHistory()
})

async function loadHistory() {
  const conv = await aiCodeApi.getConversation(props.targetType, props.targetId)
  if (conv && conv.messages) {
    messages.value = conv.messages
  }
}

async function send() {
  const text = inputText.value.trim()
  if (!text || generating.value) return

  messages.value.push({ role: 'user', content: text, timestamp: new Date().toISOString() })
  inputText.value = ''
  generating.value = true
  currentResponse.value = ''

  try {
    const resp = await aiCodeApi.generatePost({
      target_type: props.targetType,
      target_id: props.targetId,
      message: text,
      extra_entity_ids: [...props.contextEntityIds, ...extraEntityIds.value],
    })

    const reader = resp.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) return

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value, { stream: true })
      const lines = text.split('\n')

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6)
        try {
          const parsed = JSON.parse(payload)
          if (parsed.event === 'chunk') {
            currentResponse.value += parsed.content
          } else if (parsed.event === 'done') {
            messages.value.push({
              role: 'assistant',
              content: parsed.full_code,
              timestamp: new Date().toISOString(),
            })
            currentResponse.value = ''
          } else if (parsed.event === 'error') {
            messages.value.push({
              role: 'assistant',
              content: `错误：${parsed.message}`,
              timestamp: new Date().toISOString(),
            })
          }
        } catch {}
      }
      await nextTick()
      scrollToBottom()
    }
  } catch (e: any) {
    messages.value.push({
      role: 'assistant',
      content: `请求失败：${e.message || '未知错误'}`,
      timestamp: new Date().toISOString(),
    })
  } finally {
    generating.value = false
  }
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function applyCode(code: string) {
  const result = await aiCodeApi.validate(code)
  if (!result.safe) {
    const reasons = result.violations.map(v => `行${v.line}: ${v.reason}`).join('\n')
    alert(`代码安全检查未通过：\n${reasons}`)
    return
  }
  emit('apply', code)
}
</script>

<template>
  <div v-if="visible" class="ai-code-panel">
    <div class="panel-header">
      <h3>AI 代码生成</h3>
      <button class="close-btn" @click="emit('close')">×</button>
    </div>

    <div class="context-bar">
      <span class="label">上下文实体：</span>
      <select multiple v-model="extraEntityIds" class="entity-select">
        <option v-for="e in entities" :key="e.id" :value="e.id">
          {{ e.name_cn || e.name }}
        </option>
      </select>
    </div>

    <div class="chat-history" ref="chatContainer">
      <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
        <div class="message-content">
          <pre v-if="msg.role === 'assistant'"><code>{{ msg.content }}</code></pre>
          <p v-else>{{ msg.content }}</p>
        </div>
        <button
          v-if="msg.role === 'assistant' && !msg.content.startsWith('错误') && !msg.content.startsWith('请求失败')"
          class="apply-btn"
          @click="applyCode(msg.content)"
        >
          应用到编辑器
        </button>
      </div>

      <div v-if="currentResponse" class="message assistant streaming">
        <pre><code>{{ currentResponse }}</code></pre>
      </div>

      <div v-if="messages.length === 0 && !generating" class="placeholder">
        描述你想要的逻辑，例如：「根据订单列表计算最近30天的总消费金额」
      </div>
    </div>

    <div class="chat-input">
      <textarea
        v-model="inputText"
        placeholder="描述你的需求..."
        @keydown.enter.ctrl="send"
        :disabled="generating"
      />
      <button @click="send" :disabled="generating || !inputText.trim()">
        {{ generating ? '生成中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.ai-code-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 480px;
  height: 100vh;
  background: var(--bg-color, #fff);
  border-left: 1px solid var(--border-color, #e0e0e0);
  display: flex;
  flex-direction: column;
  z-index: 1000;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}
.panel-header h3 { margin: 0; font-size: 16px; }
.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}
.context-bar {
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  display: flex;
  align-items: center;
  gap: 8px;
}
.entity-select { flex: 1; min-height: 32px; }
.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.message { margin-bottom: 12px; }
.message.user p {
  background: var(--primary-light, #e3f2fd);
  padding: 8px 12px;
  border-radius: 8px;
  display: inline-block;
}
.message.assistant pre {
  background: var(--code-bg, #f5f5f5);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
}
.message.streaming pre { border: 1px solid var(--primary, #1976d2); }
.apply-btn {
  margin-top: 4px;
  font-size: 12px;
  padding: 4px 8px;
  background: var(--primary, #1976d2);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.placeholder {
  color: var(--text-secondary, #666);
  text-align: center;
  padding: 40px 20px;
}
.chat-input {
  border-top: 1px solid var(--border-color, #e0e0e0);
  padding: 12px 16px;
  display: flex;
  gap: 8px;
}
.chat-input textarea {
  flex: 1;
  resize: none;
  height: 60px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  padding: 8px;
}
.chat-input button {
  padding: 8px 16px;
  background: var(--primary, #1976d2);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  align-self: flex-end;
}
.chat-input button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/logic/AiCodePanel.vue
git commit -m "feat: add AiCodePanel component for AI-powered code generation dialog"
```

---

## Task 8: 集成到 FunctionBuilderDrawer

**Files:**
- Modify: `frontend/src/components/logic/FunctionBuilderDrawer.vue`

- [ ] **Step 1: 在 FunctionBuilderDrawer 中添加 AI 生成按钮和面板引用**

在 `<script setup>` 顶部添加 import：
```typescript
import AiCodePanel from './AiCodePanel.vue'
```

在 `form` ref 之后添加状态：
```typescript
const showAiPanel = ref(false)
```

添加回调方法：
```typescript
function onAiApply(code: string) {
  form.value.logic_body = code
  showAiPanel.value = false
}
```

- [ ] **Step 2: 在模板中 logic_body 编辑器上方添加按钮**

在 `logic_body` textarea/editor 上方添加工具栏：
```html
<div class="logic-toolbar">
  <button type="button" @click="showAiPanel = true" :disabled="!savedId && !editId">
    AI 生成
  </button>
</div>
```

- [ ] **Step 3: 在模板底部添加 AiCodePanel**

```html
<AiCodePanel
  :visible="showAiPanel"
  :target-type="'function'"
  :target-id="savedId || editId || ''"
  :context-entity-ids="form.entity_id ? [form.entity_id] : []"
  @close="showAiPanel = false"
  @apply="onAiApply"
/>
```

- [ ] **Step 4: 验证前端编译**

Run: `cd frontend && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/logic/FunctionBuilderDrawer.vue
git commit -m "feat: integrate AI code generation button into FunctionBuilderDrawer"
```

---

## Task 9: 数据库迁移

**Files:**
- Modify: `backend/app/database.py` 或启动脚本

- [ ] **Step 1: 确认自动建表机制**

该项目使用 SQLite + SQLAlchemy 的 `Base.metadata.create_all()`，新模型 import 后会自动建表。验证：

Run: `cd backend && grep -n "create_all" app/database.py app/main.py`

- [ ] **Step 2: 确认 AiCodeConversation 模型被正确 import**

由 Task 2 已在 `__init__.py` 中注册，启动应用时会自动创建表。

Run: `cd backend && python -c "from app.database import engine, Base; from app.models import AiCodeConversation; Base.metadata.create_all(engine); print('Table created')"`
Expected: `Table created`

- [ ] **Step 3: 提交**（如有修改）

若无额外改动则跳过此步。

---

## Task 10: 端到端验证

- [ ] **Step 1: 启动后端验证 API**

Run: `cd backend && python -m uvicorn app.main:app --port 8000 &`

验证端点存在：
Run: `curl -s http://localhost:8000/api/v1/ai-code/validate -X POST -H "Content-Type: application/json" -d '{"code": "result = 1+1"}' | python -m json.tool`
Expected: `{"safe": true, "violations": []}`

- [ ] **Step 2: 验证安全检查拦截危险代码**

Run: `curl -s http://localhost:8000/api/v1/ai-code/validate -X POST -H "Content-Type: application/json" -d '{"code": "import os\nresult = os.getcwd()"}' | python -m json.tool`
Expected: `{"safe": false, "violations": [{"line": 1, "reason": "Forbidden import: os"}]}`

- [ ] **Step 3: 启动前端验证编译**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build 成功

- [ ] **Step 4: 停止测试服务**

Run: `kill %1`

- [ ] **Step 5: 最终提交（如有修复）**

```bash
git add -A
git commit -m "fix: resolve integration issues from end-to-end testing"
```
