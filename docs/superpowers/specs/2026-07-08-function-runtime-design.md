# Function Runtime 独立服务化设计

## 概述

将本体平台的函数运行时抽离为独立模块，实现 12 工具三层架构中的 Tier 1（数据查询）和 Tier 2（逻辑/动作调用）能力，不实现 Tier 3（Python 代码工具箱）。

**核心目标：**
- Agent 能通过 `run_logic` / `run_action` / `list_capabilities` 调用用户定义的逻辑函数
- 用户通过 `@Function` 装饰器在 code-server 中编写函数，保存即自动注册
- 函数之间可通过注入的 `call_function` 互相调用，平台负责循环检测
- 统一三套分散的沙箱为一套

---

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Agent (LLM 智能体)                      │
│           通过 ToolRouter 调用下层工具                      │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────────┐
        ▼               ▼                   ▼
┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐
│  Tier 1      │ │  Tier 2      │ │  (Tier 3 不实现)     │
│ 数据查询工具  │ │ 逻辑/动作调用 │ │                     │
├──────────────┤ ├──────────────┤ └─────────────────────┘
│query_instances│ │run_logic     │
│complex_sql   │ │run_action    │
│get_attr_map  │ │list_capa     │
└──────┬───────┘ └──────┬───────┘
       │                │
       ▼                ▼
┌─────────────────────────────────────────────────────────┐
│          Function Runtime (独立模块)                       │
│  services/function_runtime/                              │
│  ├── registry.py      # 函数注册中心                      │
│  ├── executor.py      # 统一执行器 + call_function 注入   │
│  ├── watcher.py       # 文件监听 + AST 扫描              │
│  ├── sandbox.py       # 统一沙箱                         │
│  ├── decorator.py     # @Function 装饰器定义              │
│  └── models.py        # 运行时内部数据结构                 │
└───────────────────────┬─────────────────────────────────┘
                        │ ORM / SQL
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Database (MySQL / SQLite)                    │
└─────────────────────────────────────────────────────────┘
```

---

## @Function 装饰器

### 定义

```python
# services/function_runtime/decorator.py

def Function(
    name: str,                          # 唯一可调用名
    description: str,                   # 描述，展示给 Agent
    type: Literal["logic", "action"],   # 逻辑 or 动作
    params: list[dict] = None,          # 参数 schema
    return_type: str = "object",        # 返回值类型
):
    def wrapper(func):
        func._function_meta = {
            "name": name,
            "description": description,
            "type": type,
            "params": params,
            "return_type": return_type,
        }
        return func
    return wrapper
```

### 用户编写示例

```python
# workspace/<ontology_id>/revenue_analysis/main.py
from ontology_runtime import Function, call_function

@Function(
    name="calc_loss_factors",
    description="计算指定省分指定月份的7项折损因子",
    type="logic",
    params=[
        {"name": "prov_name", "type": "string", "required": True, "description": "省分名称"},
        {"name": "month", "type": "string", "required": True, "description": "月份 YYYYMM"},
    ],
    return_type="object",
)
def calc_loss_factors(params):
    month = params["month"]
    prov_name = params["prov_name"]
    base_data = call_function("query_bill_data", {"month": month, "prov_name": prov_name})
    # 计算逻辑...
    return {"factors": [...]}
```

### 文件结构约定

```
workspace/
├── <ontology_id>/
│   ├── <callable_name>/
│   │   └── main.py
│   ├── revenue_analysis/
│   │   └── main.py         # 可包含多个 @Function
│   └── data_export/
│       └── main.py
```

- 一个 .py 文件可包含多个 `@Function`
- `from ontology_runtime import ...` 是虚拟模块，执行时由沙箱注入
- `type="logic"` 对应 `run_logic`，`type="action"` 对应 `run_action`

---

## Function Runtime 模块设计

### Registry（注册中心）

```python
# services/function_runtime/registry.py

@dataclass
class FunctionMeta:
    callable_name: str
    description: str
    type: Literal["logic", "action"]
    params: list[ParamSchema]
    return_type: str
    source_path: str        # .py 文件路径
    func_name: str          # Python 函数名（文件内）
    ontology_id: int
    checksum: str           # 文件内容 hash，变更检测

class FunctionRegistry:
    _cache: dict[str, FunctionMeta]

    def register(self, meta: FunctionMeta, source_path: str) -> None
    def unregister(self, callable_name: str) -> None
    def get(self, callable_name: str) -> FunctionMeta | None
    def list_by_type(self, type: str, ontology_id: int = None) -> list[FunctionMeta]
    def list_capabilities(self, ontology_id: int = None) -> dict
```

### Watcher（文件监听）

```python
# services/function_runtime/watcher.py

class FunctionWatcher:
    def start(self) -> None          # 启动 watchdog 监听
    def stop(self) -> None           # 停止监听
    def scan_file(self, path: str) -> list[FunctionMeta]   # AST 解析单文件
    def scan_all(self, ontology_id: int = None) -> None    # 全量扫描
    def _on_file_changed(self, path: str) -> None          # 变更回调
```

AST 扫描逻辑：
- 解析文件 AST，找到所有带 `@Function(...)` 装饰器的函数定义
- 从装饰器参数中提取元信息
- 不执行代码，纯静态分析
- 文件删除时自动 unregister

### Executor（统一执行器）

```python
# services/function_runtime/executor.py

@dataclass
class ExecContext:
    call_stack: list[str]       # 调用链，循环检测
    max_depth: int = 10
    timeout_sec: int = 30
    ontology_id: int = None

@dataclass
class ExecResult:
    success: bool
    result: Any
    error: str | None
    execution_ms: int
    call_trace: list[str]

class FunctionRuntimeExecutor:
    def execute(self, callable_name: str, params: dict, context: ExecContext = None) -> ExecResult:
        """
        1. Registry.get(callable_name) → FunctionMeta
        2. 读取 source_path 代码
        3. 构建沙箱环境（注入 call_function、params）
        4. Sandbox.execute()
        5. 返回结果
        """

    def _build_call_function(self, context: ExecContext) -> Callable:
        """构建 call_function 闭包，内部递归调用 self.execute，含循环检测"""
```

### Sandbox（统一沙箱）

```python
# services/function_runtime/sandbox.py

class UnifiedSandbox:
    def validate(self, code: str) -> ValidationResult:
        """AST 静态检查"""

    def execute(self, code: str, func_name: str, namespace: dict, timeout: int = 30) -> Any:
        """
        1. validate() 静态检查
        2. 构建受限 __builtins__
        3. exec() 加载函数定义
        4. 调用目标函数
        5. SIGALRM 超时保护
        """
```

允许的 builtins：
`abs, max, min, round, len, int, float, str, bool, list, dict, tuple, set, range, enumerate, zip, map, filter, sorted, reversed, isinstance, print`

注入的命名空间：
```python
{
    "params": {...},
    "call_function": bound_closure,
    "call_sql": bound_sql_executor,
}
```

**`call_sql` 辅助函数规格：**
```python
def call_sql(sql: str, params: list = None) -> list[dict]:
    """
    在当前本体绑定的数据源上执行只读 SQL。
    - 只允许 SELECT 语句
    - 自动加 LIMIT 10000
    - 返回 list[dict]，每个 dict 是一行记录
    - 超时 10 秒
    """
```

**`query_instances` 内部实现依赖：**
- 复用现有 `EntityDataService`：通过 entity_name 查找实体 → 获取绑定的数据资产 → 解析物理表名和字段映射 → 构建 SQL
- 复用现有 `OntologyMapping` 模型获取属性→物理字段映射关系

---

## Agent 工具层改造

### Tier 2 新增工具

| 工具名 | 用途 | 参数 |
|--------|------|------|
| `ontology_list_capabilities` | 列出可用逻辑/动作 | type: logic/action/all |
| `ontology_run_logic` | 执行逻辑函数 | callable_name, params |
| `ontology_run_action` | 执行动作函数 | callable_name, params |

### Tier 1 重构工具

| 工具名 | 用途 | 替代 |
|--------|------|------|
| `ontology_query_instances` | 按实体查询实例（条件+分页） | 替代 query_entity_data |
| `ontology_get_attr_mapping` | 属性名→物理字段映射 | 新增 |
| `ontology_complex_sql` | 执行复杂 SQL（只读） | 替代 query_datasource |

### ToolRouter 新增 handler

- `_tool_list_capabilities` → 调用 `FunctionRegistry.list_capabilities()`
- `_tool_run_logic` → 调用 `FunctionRuntimeExecutor.execute()`，验证 type=logic
- `_tool_run_action` → 调用 `FunctionRuntimeExecutor.execute()`，验证 type=action
- `_tool_get_attr_mapping` → 查询本体属性映射
- `_tool_query_instances` → 通过实体名解析到数据源，构建 SQL
- `_tool_complex_sql` → 执行原生 SQL，自动加 LIMIT 保护

### 向后兼容

- 旧工具 `query_datasource`、`query_entity_data` 保留但标记 deprecated
- 新建 Agent 默认使用新工具集
- ToolRouter 做旧→新别名映射
- 过渡 1-2 个版本后移除旧工具

---

## 与现有系统集成

### FunctionExecutor 降级为兼容层

- expression/sql 类型：保留原有逻辑
- python 类型：委托给 FunctionRuntimeExecutor
- `execute_by_callable_name` 桥接到新运行时

### call_function 动作执行器补全

现有空壳 `action_executors/call_function.py` 改为调用 `FunctionRuntimeExecutor.execute()`。

### 三套沙箱统一

| 现有位置 | 迁移方式 |
|---------|---------|
| `function_executor.py` 内联 | 删除，走 UnifiedSandbox |
| `action_executors/custom_script.py` | 内部改用 UnifiedSandbox |
| `skill_sandbox.py` | 内部改用 UnifiedSandbox |
| `code_validator.py` | 保留，作为 validate() 补充 |

### 数据库变更

`ontology_functions` 表新增：

```sql
ALTER TABLE ontology_functions ADD COLUMN source_path VARCHAR(500) NULL;
ALTER TABLE ontology_functions ADD COLUMN func_name VARCHAR(100) NULL;
ALTER TABLE ontology_functions ADD COLUMN checksum VARCHAR(64) NULL;
ALTER TABLE ontology_functions ADD COLUMN registered_by ENUM('ui', 'watcher') DEFAULT 'ui';
```

### 平台启动流程

1. 初始化 FunctionRegistry（从 DB 加载到内存）
2. 初始化 UnifiedSandbox
3. 初始化 FunctionRuntimeExecutor
4. 启动 FunctionWatcher（全量扫描 → 增量注册）
5. ToolRouter 注入 runtime_executor

---

## 调用链路示例

### 链路 1：Agent 调用 run_logic

```
用户: "分析四川202602的收入折损因子"

Agent → list_capabilities(type="logic") → 获取可用函数列表
Agent → run_logic("calc_loss_factors", {prov_name:"四川", month:"202602"})
  → ToolRouter → FunctionRuntimeExecutor.execute()
    → Registry.get() → 读取代码 → Sandbox.validate() → Sandbox.execute()
    → 函数内 call_function("query_bill_data", {...}) → 递归执行
  → 返回 {"factors": [...]}
Agent → 生成自然语言回答
```

### 链路 2：run_action 内部编排多逻辑函数

```
Agent → run_action("generate_report", {target:"202602", base:"202502", prov_name:"四川"})
  → generate_report() 内部依次调用：
    ├─ call_function("calc_loss_factors", ...)
    ├─ call_function("funnel_analysis", ...)
    ├─ call_function("dim_contribution", ...)
    ├─ call_function("product_attribution", ...)
    └─ 组装报告 → 返回 {report_path, summary}
```

### 链路 3：循环检测

```
prov_benchmark → call_function("calc_loss_factors")
  → calc_loss_factors → call_function("prov_benchmark")  ← 检测到循环！
  → 抛出 CircularCallError，返回调用链信息
```

### 链路 4：Watcher 自动注册

```
用户保存文件 → FunctionWatcher 检测变更
  → 计算 checksum → 对比缓存 → 有变化
  → AST 扫描提取 @Function → 对比已注册函数
  → 新增/更新/移除 → Registry + DB 同步
```

---

## 错误处理与安全

### 错误分类

| 错误类型 | 触发场景 | 处理方式 |
|---------|---------|---------|
| FunctionNotFoundError | callable_name 不存在 | 返回提示，建议 list_capabilities |
| ValidationError | 代码含禁止操作 | 注册时拒绝，不入库 |
| ParamValidationError | 缺少必填参数或类型不匹配 | 返回参数 schema |
| CircularCallError | 函数互调形成环 | 中断，返回调用链 |
| MaxDepthError | 递归超过 10 层 | 中断，返回调用栈 |
| TimeoutError | 单次超过 30s | SIGALRM 中断 |
| RuntimeError | 函数内部异常 | 捕获，脱敏后返回 |
| SQLError | SQL 语法/权限错误 | 返回错误信息 |

### 安全边界

**禁止 import：**
os, sys, subprocess, shutil, socket, ctypes, importlib, pickle, shelve, multiprocessing, threading, signal, pty, fcntl, resource, tempfile, glob, pathlib, io

**禁止调用：**
open, eval, exec, __import__, compile, globals, locals, getattr, setattr, delattr, breakpoint, exit, quit

**允许 import：**
json, re, datetime, math, decimal, collections, typing, functools, itertools, statistics, copy, dataclasses

**执行限制：**
- 单函数超时：30 秒
- 调用链总超时：120 秒
- 最大递归深度：10 层
- 返回数据上限：5 MB
- SQL 自动加 LIMIT 10000
- complex_sql 只允许 SELECT

### 审计日志

每次执行记录：callable_name、params（脱敏）、result_summary（截断 1000 字符）、success、execution_ms、call_trace、triggered_by、ontology_id、created_at。

存入数据库，前端"追踪"页面可查看，与 Agent 执行追踪打通。

---

## 关键设计决策总结

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 函数定义方式 | @Function 装饰器 | 代码即配置，开发体验好 |
| Agent 调用方式 | 统一入口 run_logic/run_action | 避免工具数膨胀 |
| Tier 3 代码工具箱 | 不实现 | 所有逻辑通过正式注册提供，更安全 |
| 函数互调 | 运行时注入 call_function | 最灵活，平台做循环检测 |
| Tier 1 工具 | 重构对齐参考架构 | 三工具模式语义清晰 |
| 注册时机 | 保存时自动扫描 | 实时性好，用户无需手动操作 |
| 架构方案 | 独立服务化 | 架构清晰、沙箱统一、可测试性好 |
