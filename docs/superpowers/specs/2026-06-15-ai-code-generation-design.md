# AI 代码生成器设计规格

## 概述

为函数管理和行动管理模块增加自然语言→Python 代码生成能力。用户通过自然语言描述业务逻辑，系统结合本体上下文自动生成可执行的 Python 代码，降低使用门槛，提升编码效率。

对齐 Palantir Code Assist 理念：本体上下文驱动代码生成。

## 目标用户

- 初级用户（业务人员）：全程引导，生成后直接使用
- 高级用户（数据分析师/开发者）：用自然语言加速编码，生成后审阅修改

## 核心流程

```
用户点击"AI 生成" → 弹出对话面板（自动注入本体上下文）
→ 用户输入自然语言描述 → 后端组装 prompt → SSE 流式生成代码
→ 用户可多轮迭代 → 点击"应用" → 静态安全分析
→ 通过则写入编辑器 → 用户可测试验证 → 保存
```

## 一、本体上下文注入

### 上下文来源（三部分）

1. **函数的 entity_id**（自动）— 主实体及其全部属性结构
2. **参数中引用的实体**（自动）— 遍历 input_schema，提取每个参数的 entity_id 对应的实体
3. **用户手动补充的实体**（可选）— 对话面板顶部提供多选实体选择器

### 注入内容

每个实体注入以下信息：
- 实体名称、描述
- 全部属性列表（属性名、数据类型、描述、约束）

### 未关联实体的处理

- 有 entity_id → 自动注入，显示"上下文：客户(Customer)"
- 无 entity_id → 显示提示 + 可选的实体选择器
  - 用户选了 → 注入上下文（不修改函数本身的 entity_id）
  - 用户跳过 → 仅用参数定义生成

## 二、数据模型

新增 `ai_code_conversations` 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| target_type | string | "function" 或 "action" |
| target_id | string | 关联的函数/行动 ID |
| messages | JSON | 对话记录数组 [{role, content, timestamp}] |
| context_entity_ids | JSON | 本次对话注入的实体 ID 列表 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

对话历史绑定到具体的函数/行动实例，跨会话保留。

## 三、API 设计

### 3.1 流式代码生成

```
POST /api/ai-code/generate (SSE)
Body: {
  target_type: "function" | "action",
  target_id: string,
  message: string,
  extra_entity_ids: string[]
}
Response: SSE stream
  → {event: "chunk", data: "代码片段"}
  → {event: "done", data: {full_code, conversation_id}}
```

### 3.2 获取对话历史

```
GET /api/ai-code/conversations/{target_type}/{target_id}
Response: {id, messages, context_entity_ids, updated_at}
```

### 3.3 代码安全检查

```
POST /api/ai-code/validate
Body: {code: string}
Response: {safe: boolean, violations: [{line, reason}]}
```

### 3.4 函数测试

```
POST /api/functions/{id}/test
Body: {params: {...}}
Response: {success, value, error, execution_ms}
```

行动测试复用现有 dry_run 机制。

## 四、前端组件

### 4.1 入口

函数/行动编辑页的 logic_body 编辑器工具栏：`[AI 生成] [测试]`

### 4.2 AI 对话面板（Drawer 抽屉）

```
AiCodePanel (从右侧滑出)
├── ContextBar (顶部：已注入实体标签 + 手动添加实体选择器)
├── ChatHistory (对话记录：用户消息 + AI 回复，代码块高亮)
├── ChatInput (输入框 + 发送按钮 + 中断按钮)
└── ActionBar ("应用到编辑器" 按钮)
```

交互细节：
- 流式生成时逐步渲染代码，显示打字光标效果
- 生成完成后代码块右上角出现"应用"按钮
- 点击"应用" → validate → 通过则填入编辑器并高亮变更
- 首次打开显示引导提示："描述你想要的逻辑，例如：'根据订单列表计算最近30天的总消费金额'"

### 4.3 测试面板

点击"测试"按钮弹出：
- 上半部分：根据 input_schema 自动生成参数表单
- 执行按钮
- 下半部分：执行结果展示
  - 成功 → 返回值 + 执行耗时
  - 失败 → 错误信息 + 堆栈 + 通俗解释

## 五、Prompt 工程

### System Prompt

```
你是一个 Python 代码生成助手，为本体平台的函数/行动生成执行逻辑。

规则：
- 生成纯 Python 代码，不要 markdown 包裹
- 通过 params 字典获取输入参数，结果写入 result 变量
- 只允许使用以下模块：math, datetime, json, re, decimal, collections
- 不允许文件操作、网络请求、系统调用
- 代码简洁，必要时加简短中文注释
- 如果用户描述模糊，先反问澄清而不是猜测生成
```

### User Prompt 模板

```
## 当前函数信息
名称：{function_name}
描述：{description}
返回类型：{return_type}
输入参数：
{input_schema 格式化}

## 本体上下文
{逐个实体展开：实体名 + 属性列表(名称/类型/描述)}

## 对话历史
{最近10轮对话记录}

## 用户需求
{用户本次输入}
```

### 关键策略

- 本体上下文按实体分块，结构清晰
- 对话历史保留最近 10 轮，避免 token 溢出
- LLM 对模糊描述应反问澄清

## 六、安全机制

### 6.1 静态分析（AST 白名单）

允许的 import：math, datetime, json, re, decimal, collections

禁止的模式：
- import os / sys / subprocess / shutil
- open() / 文件 I/O
- eval() / exec()（禁止嵌套执行）
- __import__()
- 网络相关：socket, requests, urllib, http

### 6.2 执行沙箱加固

- 执行时间限制：5秒超时
- 内存限制：通过 resource 模块
- __builtins__ 裁剪为安全子集

### 6.3 分层拦截

1. LLM 生成时 → system prompt 约束（软限制）
2. 用户点"应用"时 → AST 静态分析（硬限制）
3. 执行时 → 沙箱隔离（兜底保护）

## 七、决策记录

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 目标用户 | 初级 + 高级 | 覆盖面最广 |
| 上下文范围 | 参数 + 关联实体属性 | 平衡语义丰富度和 token 成本 |
| 交互模式 | 对话迭代 → 应用到编辑器 | 初级用户安全迭代，高级用户保留控制 |
| 安全策略 | 静态分析 + 试运行 | 双层防护，成本低效果好 |
| 入口位置 | 编辑器上方按钮 | 上下文即入口，自动注入 |
| 调用方式 | 后端 SSE 流式 | 安全 + 体验好，复用现有 SSE 基础设施 |
| 对话持久化 | 绑定实例，跨会话 | 支持渐进式迭代完善 |
| 上下文实体 | 多实体（自动 + 手动） | 真实场景常涉及多实体 |
| 测试能力 | 独立测试按钮 | 所有函数通用，不限于 AI 生成 |
