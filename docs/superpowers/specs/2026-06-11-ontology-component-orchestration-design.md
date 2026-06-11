# 本体组件编排与技能集成设计规格

## 概述

将本体平台中的 Rule（规则）、Function（函数）、Action（行动）三类组件纳入已有的版本发布体系，使流程编排和技能管理能够以类型安全的方式引用已发布的组件实例。

## 设计决策

| # | 决策 | 依据 |
|---|------|------|
| 1 | 流程编排新增 Function / Rule / Action 三种独立节点 | 三者语义不同：纯计算 / 条件判断 / 副作用执行 |
| 2 | Rule 节点在流程中只做纯判断（true/false），不自动执行绑定的 action | 编排层需要完整控制权，同一规则在不同流程中可触发不同动作 |
| 3 | 技能管理可引用 Function / Rule / Action 全部三者作为 Agent 工具 | Rule 提供权威判定（避免 LLM 幻觉），Function 提供计算，Action 提供执行 |
| 4 | 删除草稿源时软引用 + 预警 | 不阻塞操作流，但给用户足够信息 |
| 5 | 参数映射采用可视化下拉 + 表达式两层模式 | 治理平台需要显式可审计的映射，自动推荐有歧义风险 |
| 6 | 参数定义锚定本体模型的实体属性 | 本体作为统一语义层，确保类型安全和语义明确 |
| 7 | 流程编排和技能管理只引用已发布的本体版本 | 草稿可变，发布版本冻结，保证运行时稳定性 |

## 实现方案：分类型快照表（方案 A）

沿用现有 `OntologyVersionEntity` / `OntologyVersionAttribute` / `OntologyVersionRelation` 的模式，为 Function / Rule / Action 各创建版本快照表，发布时拷贝不可变副本。

---

## 一、数据模型

### 1.1 层级关系

```
OntologyVersion (已有)
 ├── OntologyVersionEntity (已有)
 │    └── OntologyVersionAttribute (已有)
 ├── OntologyVersionRelation (已有)
 ├── OntologyVersionFunction (新增)
 ├── OntologyVersionRule (新增)
 └── OntologyVersionAction (新增)
          ↓ 被引用
 WorkflowDefinition.nodes[] (扩展)
 SkillToolRef (新增)
```

### 1.2 OntologyVersionFunction

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | 快照 ID |
| version_id | FK → ontology_versions.id | 所属发布版本 |
| source_function_id | String(36) | 草稿源 function ID |
| version_entity_id | FK → ontology_version_entities.id | 所属实体快照 |
| name | String(200) | 函数名 |
| description | Text | 描述 |
| return_type | String(50) | 返回值类型 |
| input_schema | JSON | 参数列表，每项含 {name, type, version_attribute_id, required, default_value, description} |
| logic_type | String(30) | expression / sql / python |
| logic_body | Text | 执行逻辑体 |
| callable_name | String(100) | 可调用标识 |
| tags | JSON | 标签 |

### 1.3 OntologyVersionRule

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | 快照 ID |
| version_id | FK → ontology_versions.id | 所属发布版本 |
| source_rule_id | String(36) | 草稿源 rule ID |
| version_entity_id | FK → ontology_version_entities.id | 所属实体快照 |
| name | String(200) | 规则名 |
| description | Text | 描述 |
| condition_expr | Text | 条件表达式（文本形式） |
| conditions_json | JSON | 结构化条件，每项含 {field, operator, value, version_attribute_id} |
| priority | String(10) | high / medium / low |
| input_params | JSON | 输入参数，每项含 {name, type, version_attribute_id, required} |
| output_schema | JSON | 输出结构定义 |
| tags | JSON | 标签 |

### 1.4 OntologyVersionAction

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | 快照 ID |
| version_id | FK → ontology_versions.id | 所属发布版本 |
| source_action_id | String(36) | 草稿源 action ID |
| version_entity_id | FK → ontology_version_entities.id (nullable) | 所属实体快照，system 类行动为 null |
| name | String(200) | 行动名 |
| category | String(20) | domain / system |
| action_type | String(30) | api_call / sql_exec / modify_attribute / notification / call_function / custom_script |
| type_config | JSON | 行动类型配置 |
| description | Text | 描述 |
| parameters_json | JSON | 参数列表，每项含 {name, type, version_attribute_id, required, default_value, description} |
| output_schema | JSON | 输出结构定义 |

### 1.5 SkillToolRef

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | |
| skill_id | FK → skills.id | 所属技能 |
| version_id | FK → ontology_versions.id | 绑定的本体版本 |
| ref_type | String(20) | function / rule / action |
| ref_id | String(36) | 指向 OntologyVersionFunction/Rule/Action 的 id |
| alias | String(100) | Agent 调用时的工具名称 |
| description | Text | 工具描述（传给 LLM 的 tool description） |
| param_override | JSON | 可覆盖部分参数的默认值 |
| created_at | DateTime | |

### 1.6 流程定义版本绑定

现有流程/场景模型需新增字段：

| 模型 | 新增字段 | 类型 | 说明 |
|------|---------|------|------|
| AipScene / WorkflowDefinition | ontology_version_id | FK → ontology_versions.id (nullable) | 该流程绑定的本体版本，null 表示未绑定（旧数据兼容） |

流程编辑器打开时：
- 如果 ontology_version_id 为 null，提示用户选择版本
- 如果已绑定版本，节点选择器只展示该版本的 F/R/A
- 如果绑定的版本非当前活跃版本，顶部提示"有新版本可用"

### 1.7 WorkflowNode 扩展字段

现有流程定义的 nodes JSON 数组中，每个节点增加以下字段：

```json
{
  "id": "node_xxx",
  "type": "function-call | rule-evaluate | action-execute",
  "position": { "x": 300, "y": 200 },
  "data": {
    "label": "计算客户风险等级",
    "version_id": "ver_abc",
    "ref_type": "function",
    "ref_id": "vf_123",
    "param_mapping": {
      "credit_score": {
        "source": "node",
        "node_id": "node_prev",
        "field": "output.credit_score"
      },
      "transaction_amount": {
        "source": "expression",
        "expr": "{{nodes.query_node.output.amount * 0.8}}"
      }
    },
    "output_var": "risk_level"
  }
}
```

---

## 二、流程编排节点集成

### 2.1 节点类型定义

| 节点 type | 标签 | 语义 | 输入 | 输出 |
|-----------|------|------|------|------|
| `function-call` | 函数调用 | 执行已发布函数，返回计算结果 | param_mapping 映射的参数 | `{success, value, execution_ms}` 写入 output_var |
| `rule-evaluate` | 规则评估 | 评估已发布规则条件，纯判断 | param_mapping 映射的参数 | `{triggered: bool, confidence, conditions: [...]}` |
| `action-execute` | 行动执行 | 执行已发布行动的副作用 | param_mapping 映射的参数 | `{success, message, output}` |

### 2.2 Rule 节点分支连线

Rule 节点有两个输出端口：
- Right handle (id=`"true"`) — 条件满足时走此分支
- Bottom handle (id=`"false"`) — 条件不满足时走此分支

复用现有 `condition` 节点的双出口模式。

### 2.3 param_mapping 规范

每个参数支持三种 source 类型：

| source | 含义 | 配置字段 |
|--------|------|---------|
| `node` | 上游节点输出字段 | node_id + field（点分路径） |
| `variable` | 流程全局变量 | var_name |
| `expression` | 模板表达式 | expr（支持 `{{}}` 语法） |

表达式语法支持：
- 变量引用：`{{nodes.<node_id>.output.<field>}}`、`{{vars.<var_name>}}`
- 简单运算：`{{nodes.a.output.amount * 0.8}}`
- 字符串拼接：`{{nodes.a.output.first_name + " " + nodes.a.output.last_name}}`

### 2.4 执行引擎调度

```
function-call 节点执行流程:
  1. 根据 ref_id 从 OntologyVersionFunction 加载函数定义
  2. 根据 param_mapping 从执行上下文 (context) 解析各参数实际值
  3. 调用 FunctionExecutor.execute(func_definition, resolved_params)
  4. 将 FunctionResult 写入 context[output_var]
  5. 流程引擎继续沿 source handle 前进

rule-evaluate 节点执行流程:
  1. 根据 ref_id 从 OntologyVersionRule 加载规则定义
  2. 根据 param_mapping 解析参数
  3. 调用 RuleEvaluator.evaluate(rule_definition, resolved_params)
  4. 返回 RuleResult {triggered, conditions, confidence}
  5. 流程引擎根据 triggered 值选择 true 或 false 分支边

action-execute 节点执行流程:
  1. 根据 ref_id 从 OntologyVersionAction 加载行动定义
  2. 根据 param_mapping 解析参数
  3. 检查是否为 dry_run 模式（调试/预览时不实际执行）
  4. 调用对应 ActionExecutor (api_call / sql_exec / ...)
  5. 将 ActionExecuteResult 写入上下文
```

---

## 三、技能管理集成

### 3.1 技能工具注册

技能编辑页面新增"本体工具"标签页：
1. 选择本体版本（默认当前活跃版本 `is_active=true`）
2. 按类型分组展示该版本下所有可用的 Function / Rule / Action
3. 用户勾选后创建 SkillToolRef 记录
4. 可配置 alias（Agent 看到的工具名）和 description（工具描述）

### 3.2 Agent 执行时工具构建

技能执行器 `skill_executor.py` 构建 Agent 工具列表时：

```
对于每个 SkillToolRef:
  1. 根据 ref_type + ref_id 加载 OntologyVersionFunction/Rule/Action 定义
  2. 将 input_schema / parameters_json / input_params 转为 JSON Schema 格式
  3. 注册为 LLM 可调用的 tool:
     - name: alias
     - description: ref.description 或原始组件 description
     - parameters: 转换后的 JSON Schema
  4. 执行路由:
     - ref_type="function" → FunctionExecutor.execute()
     - ref_type="rule" → RuleEvaluator.evaluate()
     - ref_type="action" → ActionExecutor.execute()
  5. 返回值作为 tool_result 回传给 LLM
```

### 3.3 工具执行结果格式

| ref_type | 返回给 Agent 的结果 |
|----------|-------------------|
| function | `{"success": true, "value": <computed_value>, "execution_ms": 12.5}` |
| rule | `{"triggered": true, "confidence": 0.95, "conditions": [{"field": "信用评分", "operator": "<", "expected": 60, "actual": 45, "matched": true}]}` |
| action | `{"success": true, "message": "通知已发送", "output": {...}}` |

---

## 四、定义层增强（前置改造）

### 4.1 Function input_schema 增强

当前结构：
```json
[{"name": "amount", "type": "number", "required": true}]
```

增强后：
```json
[{
  "name": "amount",
  "type": "number",
  "required": true,
  "default_value": null,
  "description": "交易金额",
  "entity_id": "entity_customer",
  "attribute_id": "attr_transaction_amount"
}]
```

### 4.2 Rule conditions_json 增强

当前结构：
```json
[{"field": "credit_score", "operator": "<", "value": 60}]
```

增强后：
```json
[{
  "field": "credit_score",
  "operator": "<",
  "value": 60,
  "entity_id": "entity_customer",
  "attribute_id": "attr_credit_score"
}]
```

### 4.3 Action parameters_json 增强

与 Function input_schema 相同模式，每项增加 `entity_id` + `attribute_id`。

### 4.4 前端参数编辑器改造

函数/规则/行动的参数配置 UI 中，每个参数增加"关联实体属性"选择器：
1. 显示当前组件绑定实体的属性列表（优先）
2. 允许跨实体选择（如函数可能需要多个实体的属性）
3. 选择后自动填充 type（attribute.type → param.type）
4. attribute_name 用于前端显示和发布快照时的可读性

---

## 五、发布流程扩展

### 5.1 快照逻辑

在现有 `add_entities` 接口旁增加快照方法：

```
POST /ontology-publish/versions/{version_id}/snapshot-components

执行逻辑:
  1. 获取该版本已包含的所有 version_entity
  2. 对每个 version_entity:
     a. 查询其 source_entity_id 关联的所有 active Function
        → 创建 OntologyVersionFunction 快照
        → input_schema 中的 attribute_id 映射为 version_attribute_id
     b. 查询关联的所有 active Rule
        → 创建 OntologyVersionRule 快照
        → conditions_json 中的 attribute_id 映射为 version_attribute_id
     c. 查询关联的所有 active Action
        → 创建 OntologyVersionAction 快照
        → parameters_json 中的 attribute_id 映射为 version_attribute_id
  3. 查询 category="system" 的全局 Action（无实体绑定）
     → 创建快照，version_entity_id 为 null
```

### 5.2 一致性检查扩展

现有 `consistency_check` 接口增加以下检查项：

| 检查项 | 说明 | 级别 |
|--------|------|------|
| 函数参数属性完整性 | input_schema 引用的 attribute_id 是否都在该版本实体中 | ERROR |
| 规则条件属性完整性 | conditions_json 引用的 attribute_id 是否都在该版本中 | ERROR |
| 行动参数属性完整性 | parameters_json 引用的 attribute_id 是否都在该版本中 | ERROR |
| 规则关联行动存在性 | 规则草稿上的 action_id 对应的行动是否也在该版本中 | WARNING |
| 函数调用行动存在性 | call_function 类型行动引用的 callable_name 是否存在 | WARNING |

### 5.3 attribute_id → version_attribute_id 映射

发布快照时需要做 ID 转换：

```
草稿态: entity_id="e1", attribute_id="a1"
发布态: version_entity_id="ve1", version_attribute_id="va1"

映射关系:
  OntologyVersionAttribute.source_attribute_id = "a1"
  → 在同版本中找到 version_attribute_id = "va1"
```

---

## 六、治理与版本升级

### 6.1 删除预警

用户在规则/函数/行动管理中删除时，后端返回影响分析：

```
GET /api/v1/functions/{id}/impact-analysis
GET /api/v1/rules/{id}/impact-analysis
GET /api/v1/actions/{id}/impact-analysis

响应:
{
  "published_versions": ["v2.3", "v2.4"],
  "referencing_workflows": [
    {"id": "wf1", "name": "风险评估流程", "version": "v2.3"}
  ],
  "referencing_skills": [
    {"id": "sk1", "name": "风控Agent", "version": "v2.3"}
  ],
  "safe_to_delete": true,
  "message": "删除草稿源不影响已发布版本的运行，但该组件将不会出现在未来新版本中"
}
```

前端弹窗展示上述信息，用户确认后执行删除。

### 6.2 版本升级兼容性检查

```
GET /ontology-publish/versions/{new_version_id}/upgrade-check?from_version_id={old_version_id}

响应:
{
  "compatible_workflows": ["wf1", "wf2"],
  "breaking_workflows": [
    {
      "id": "wf3",
      "name": "客户分级流程",
      "breaking_reasons": [
        {"node_id": "n1", "ref_type": "function", "reason": "参数 credit_score 类型从 number 变更为 string"},
        {"node_id": "n3", "ref_type": "action", "reason": "行动 send_alert 已从新版本中移除"}
      ]
    }
  ],
  "compatible_skills": ["sk1"],
  "breaking_skills": []
}
```

### 6.3 兼容性判定规则

| 变更类型 | 判定 | 自动升级 |
|---------|------|---------|
| 组件新增 | 兼容 | 是 |
| 函数增加可选参数（required=false） | 兼容 | 是 |
| 函数删除参数 | 不兼容 | 否，需人工处理 |
| 函数参数类型变更 | 不兼容 | 否 |
| 函数逻辑体变更（logic_body） | 兼容（接口不变） | 是 |
| 函数整体删除 | 不兼容 | 否，必须替换节点 |
| 规则条件变更 | 兼容（输出仍为 bool） | 是 |
| 规则输入参数变更 | 不兼容 | 否 |
| 规则整体删除 | 不兼容 | 否 |
| 行动参数变更 | 不兼容 | 否 |
| 行动类型变更 | 不兼容 | 否 |
| 行动整体删除 | 不兼容 | 否 |

### 6.4 升级操作

```
POST /ontology-publish/workflows/{workflow_id}/upgrade
Body: { "target_version_id": "ver_new" }

执行逻辑:
  1. 对每个引用节点，查找 target_version 中 source_*_id 相同的快照
  2. 兼容的节点: 自动更新 ref_id 和 version_id
  3. 不兼容的节点: 返回错误列表，要求人工处理
  4. 全部处理完成后，更新 workflow 的 version_id 绑定
```

---

## 七、改造范围与优先级

| 优先级 | 改造项 | 涉及文件 | 说明 |
|--------|--------|---------|------|
| P0 | 定义层增强 | models/function.py, models/rule.py, schemas/*, 前端参数编辑器 | 前置条件，其他改造依赖此项 |
| P0 | 版本快照表 | models/version.py, api/v1/ontology_publish.py | 新增三张表 + 快照逻辑 |
| P1 | 流程编排节点 | WorkflowNode.vue, 流程执行引擎, 节点配置面板 | 核心功能 |
| P1 | 技能工具引用 | models/skill_tool.py → skill_tool_ref, skill_executor.py, 技能编辑UI | 核心功能 |
| P2 | 删除预警 | function/rule/action 的 API 层 + 前端弹窗 | 治理保障 |
| P2 | 版本升级检查 | ontology_publish.py, 前端升级引导 | 治理保障 |
| P2 | 一致性检查扩展 | ontology_publish.py consistency_check | 质量门禁 |

