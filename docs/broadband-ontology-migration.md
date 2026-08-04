# broadband 场景本体化改造方案

## 一、现状诊断

`backend/app/api/v1/broadband/` 是平台的旗舰演示场景（宽带装机退单稽核），但它**不经过本体层**。

### 1.1 证据

- `grep -rn "OntologyEntity|entity_relations|entity_attributes|ObjectBinding" backend/app/api/v1/broadband/` → **0 处命中**
- 物理表名以字面量形式散布在代码中：`bb_install_churn`、`bb_install_order`、`bb_customer` 等 16 张表
  - `routes.py`：74 处 SQL，其中 18 处含 JOIN、25 处含聚合
  - `analysis.py`：21 处 SQL
- 数据访问经 `db.py:25` 的 `_BB_CONN_NAME = "bb_audit_db"` 直接取 Connection，走 `ExecuteService.execute_on_connection`，绕过 `EntityDataService`
- 归因算法是 Python 手写字典与分支：`analysis.py:241-289` 的 `CAUSE_EVIDENCE_MAP`、`L2_MAP`，`analysis.py:30-131` 的 `_make_todos()`
- `LF-001`~`LF-007` 在 `routes.py:368-401` 仅作为字符串标签用于前端展示进度，从未被当作逻辑函数执行

**结论：清空数据库中全部本体数据，broadband 所有接口照常返回结果。**

### 1.2 平行世界

| | 世界 A：本体驱动 | 世界 B：broadband |
|---|---|---|
| 入口 | `workspace/` 下的逻辑函数 | `/api/v1/scenes/broadband/*` |
| 数据访问 | `query_object()` → `ObjectBinding` → `Asset.locator` → `EntityAttribute` 字段映射 | 硬编码 SQL |
| 归因逻辑 | `run_inference_engine` 等函数 | `analysis.py` 手写规则 |
| 依赖本体 | 是（清空即失效） | 否 |
| 是否入 git | 否（`.gitignore:39` 排除，运行时产物） | 是 |

两套实现之间没有任何代码引用，仅靠对象名字符串巧合（`InstallChurn` 等）看起来相关。

### 1.3 阻塞性前置问题：绑定缺失

`backend/scripts/seed_business_assets.py:105-118` 只注册了 Asset（`bb.churn` → `bb_install_churn` 等 14 张表），**没有创建任何 ObjectBinding**。

而 `EntityDataService.resolve_entity_asset`（`entity_data_service.py:40-47`）依赖 `ObjectBinding(role=primary)` 才能把本体对象解析到物理表。

即：**当前环境下本体对象与 bb_* 资产之间没有绑定关系**，`query_object("InstallChurn")` 能工作只是因为有人在开发机界面上手工绑过；全新部署环境中这层是空的。

绑定能力本身是齐的，可由用户在界面完成：
- 后端 `POST /api/v1/object-bindings`（`app/api/v1/data_plane/object_bindings.py:43`）
- 前端 `frontend/src/api/binding.ts:20`

### 1.4 已知副作用（需一并决策）

上一步已删除的 `frontend/public/ontology_template.json`，此前是把这套退单稽核本体（14 对象 / 13 关系 / 13 动作）导入数据库的**唯一现成来源**。删除后，新环境需要另行建立这些对象，否则世界 A 的 `workspace/` 函数同样无法解析对象。

可选替代路径见「五、待决策项」。

---

## 二、改造目标

让 broadband 场景真正依赖本体：**清空本体数据后，broadband 接口应当失败或明确报错，而不是照常返回结果。** 这是唯一可验收的成功标准。

---

## 三、关键技术发现

`EntityDataService.execute_ontology_sql`（`entity_data_service.py:193-267`）**已经支持用本体对象名书写原生 SQL（含多表 JOIN）**：

1. 将 SQL 中作为标识符出现的对象名替换为物理表名（长名优先，避免前缀误匹配）
2. 收集 SQL 引用到的全部 asset，并入白名单
3. 走 `ExecuteService`，保留 AST 校验、参数化、限流、审计、列级脱敏

这意味着 `routes.py` 的 95 处 SQL **不需要重写为 ORM 或 DSL**，只需把 `FROM bb_install_churn` 改为 `FROM InstallChurn`，改造是机械的、可逐个接口验证的。

**限制**：该方法只重写表名，**不重写字段名**。改造后 SQL 仍耦合物理列名。彻底解耦需扩展其支持 `对象.属性` → `表.列`（`get_attr_field_map` 已提供映射，`entity_data_service.py:52-63`）。

---

## 四、分阶段方案

### 阶段 0：建立绑定（前置，必做）

- 为 14 个 bb_* 资产与对应本体对象建立 `ObjectBinding(role=primary)`
- 补齐 `EntityAttribute` 的物理列映射（`source_field`）
- **推荐方式**：由用户在界面完成绑定，符合「本体由界面动态构建」的原则；若需可重复部署，可提供一次性可重放脚本，但脚本产出的是用户数据、不应随启动流程自动执行

验收：`POST /object-bindings/{id}/test-resolve` 对 14 个对象全部通过

风险：低。纯新增数据，不改代码。

### 阶段 1：表名本体化（主体工作量）

将 `routes.py`、`analysis.py` 的数据访问从 `db._query` 切到 `EntityDataService.execute_ontology_sql`，SQL 中物理表名替换为本体对象名。

- 改造面：95 处 SQL 调用点，18 处 JOIN 需确认多 asset 白名单生效
- `db.py` 保留为薄封装，但 `_resolve_connection_id` 路径改为经本体解析
- 逐接口验证：18 个接口（overview / list / detail / stats / audit / evidence / chain / actions / approve / reject / feedback / re-attribute / inbox / workbench / voice-audit / analyze 等）

验收：清空 `object_bindings` 表后，broadband 接口返回明确错误而非数据

风险：中。SQL 重写可能触发 ExecuteService 的 AST 白名单差异，需逐个回归。建议按接口分批提交。

### 阶段 2：字段本体化（可选，彻底解耦）

扩展 `execute_ontology_sql` 支持 `对象名.属性名` → `物理表.物理列` 重写，复用 `get_attr_field_map`。

- 改造面：`entity_data_service.py` 新增重写逻辑 + 95 处 SQL 的字段名替换
- 收益：物理表结构变更不再需要改业务代码

风险：中高。字段名重写的歧义处理（别名、聚合表达式、子查询）需要充分测试。

### 阶段 3：归因逻辑本体化（核心，需先决策）

`analysis.py` 的 `CAUSE_EVIDENCE_MAP`、`L2_MAP`、`_make_todos()` 是写死在代码里的业务规则，本应是本体资产。两条路线：

**路线 A：规则数据化**
- 规则移入数据库（作为本体的证据-根因映射配置），`analysis.py` 退化为执行引擎
- 优点：规则可由业务人员在界面维护，符合平台定位
- 代价：需设计规则存储模型与维护界面

**路线 B：规则函数化**
- 改为调用函数运行时执行 `run_inference_engine` 等逻辑函数（世界 A 已有实现）
- 优点：复用既有实现，两套世界合并
- 代价：`workspace/` 是运行时产物、不入 git，新环境为空；需要逻辑函数的导出/导入分发机制

验收：修改规则数据后，归因结果随之变化，无需改代码、无需重启

风险：高。涉及业务语义正确性，需与业务方确认规则等价。

---

## 五、待决策项

1. **阶段 3 走路线 A 还是 B**，或先只做阶段 0-1
2. **退单稽核本体如何进入新环境**：界面手工重建 / 一次性迁移脚本（脚本产出用户数据，用后即弃）/ 从已注册资产表结构反向生成对象
3. **`main.py:372-375` 的 seed 业务数据（4 个智能体、2 个技能、3 个 AIP 场景）如何处理** —— 与本方案同源问题，本次未纳入范围
4. 是否保留 `db.py` 作为兼容层，还是彻底删除

---

## 六、工作量与建议顺序

| 阶段 | 工作量 | 风险 | 建议 |
|---|---|---|---|
| 0 建立绑定 | 小 | 低 | 立即做，且是后续所有阶段的前提 |
| 1 表名本体化 | 大（95 处） | 中 | 分批做，按接口提交 |
| 2 字段本体化 | 中 | 中高 | 阶段 1 稳定后再评估 |
| 3 归因本体化 | 大 | 高 | 先决策路线，再单独立项 |

建议先完成阶段 0，用 `test-resolve` 验证绑定链路真实可用，再启动阶段 1。阶段 0 完成后即可获得一个可验证的事实：本体层是否真的能解析到这些业务表。
