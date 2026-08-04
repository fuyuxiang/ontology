# 退单稽核场景结构说明

> 本文档**取代**此前以「broadband 模块本体化改造」为题的同名文件。直接连生产库核对后，确认前一版整套分析前提错误（错把开发态 demo 当成生产链路），本版重写。

## 一、实际生产部署（数据库直连确认）

退单稽核在生产上**完整运行**，链路如下：

### 1.1 本体层

| 项 | 状态 |
|---|---|
| `ontology_entities` 中 11 个 published 对象 | `Address / CallbackCall / Channel / Customer / DispatchRecord / Engineer / EngineerCall / InstallChurn / InstallOrder / MarketingCall / PendingPool` |
| `ontology_versions` 1 个发布版本 | `2e70c9de-4c8a-...`，名称「宽带退单原因稽核」，`status=published`，2026-07-12 发布 |
| `ontology_version_entities` | 11 行（对应上述对象）|
| `object_bindings` | 14 条 `role=primary status=active`，全部 `id_column` 填好，绑到 `DWD_D_ONT_*` 真实 ODS/DWD 表 |
| `entity_attributes` | 148 条，147 条带 `source_table / source_field` 物理列映射 |

### 1.2 运行时（workspace/）

7 个本体驱动函数由 FunctionWatcher 自动从 `workspace/*/main.py` 加载并注册到 `OntologyFunction`：

```
audit_single_order / accept_cancellation_audit / run_inference_engine
compute_rule_evidence / collect_order_context / extract_call_evidence / batch_audit
```

注册元数据全部 `registered_by=watcher`、`logic_type=python`、`status=active`。

### 1.3 对外暴露

业务系统通过 ontology 平台动态生成的端点消费：

- `POST /ontology-api/query`（`backend/app/api/v1/ontology_api.py:101`）
- `GET /ontology-api/objects/{entity.name}`（同文件 `:41` 由 published 实体动态生成）
- tool_router 经 Agent 工具调用链触发：`backend/app/services/agent/orchestrator.py:42` → `ToolRouter.execute` → `workspace` 函数

**生产上完整链路 = 11 个 published 对象 + 14 条 binding + 7 个 watcher 注册函数 + ontology-api 动态端点。**

## 二、已删除的「`broadband` 模块」

此前 `backend/app/api/v1/broadband/` 整个目录（1500 行）属于**早期开发态 demo**，已经下线：

### 2.1 它为什么不属于生产

| 维度 | 状态 |
|---|---|
| 物理表 | 95 处硬编码 SQL 引用的全是 `bb_*` 表；这些表由 `scripts/bb_init_db.py` 在 `127.0.0.1:3307/bb_churn_audit` 造数，**生产库不存在** |
| 前端页面 | `frontend/src/router/index.ts` 全部 30 条路由都是平台内部建模界面，**0 个**调 `broadband` API |
| 后端 import | `grep "from app.api.v1.broadband import"` 仅命中 `main.py` 旧版第 132 行（注册 router 本身），**0 处**真实业务调用 |
| Agent/Skill | `audit_single_order` 等函数在 backend 内部（非 workspace）**0 处**引用 |
| 数据库 | `assets` 表 `bb.*` count=0；`bb_audit_db` Connection 在生产上未注册 |

### 2.2 清理动作（已提交）

- 删除 `backend/app/api/v1/broadband/` 整个目录（4 个源文件 + pycache）
- 删除 `scripts/bb_*.py` + `bb_create_tables.sql`（开发态造数工具 6 个文件）
- `backend/app/main.py` 摘掉 `broadband_router` 的 import 和 `include_router`，注释同步更新

### 2.3 为什么不用"本体化改造"

之前那份同名方案要做的「把 95 处硬编码 SQL 改走 `EntityDataService`」**前提就是错的**——这套代码根本没在生产上跑，改造没意义。真正在生产上跑的本体驱动链路（workspace + ontology-api）已经是本体驱动的，不需要改造。

## 三、本体驱动链路上值得加固的事

虽然 1.1~1.3 已经成立，但有两处可改进：

### 3.1 `workspace/` 是运行时产物

`workspace/*/main.py` 7 个退单稽核函数在开发机文件系统上，git 只跟踪 `workspace/.gitkeep` 和 `workspace/sample/calc_demo/`（`.gitignore:39` 排除 `workspace/*/`）。风险：

- 开发机故障 / 重装 = 生产配置丢失（虽然 `OntologyFunction` 表有元数据，但 `source_path` 指向的文件不在了）
- 团队多人协作无法代码评审

**建议**：把 `workspace/audit_single_order/` 等目录加进版本控制，删除 `.gitignore` 中的排除规则；或定期导出到 `docs/` 作为快照。

### 3.2 对象已发布但属性映射手工维护

`entity_attributes` 中 147 条 `source_table/source_field` 是用户在界面上手工填的（`ObjectBindingService.create` 自动镜像 + 人工补充）。DDL 变更时无自动跟随机制——这是当前真正未解决的「本体驱动 vs 物理 schema 漂移」问题。

**建议**：增加 `python -m scripts.sync_attr_field_maps` 一类工具，对比 Asset 的 `schema_snapshot` 与当前 `EntityAttribute.source_field`，给出 diff 报告；不自动改，给人工评审。

## 四、被 seed 误导的 4 张表（已核实的现状）

之前 `_seed_agents / _seed_skills / _seed_aip_scenes / _seed_templates` 在空库启动时无条件插入业务数据，已删除。删除后查询生产库：

| 表 | 当前行数 | 来自旧 seed | 用户自建 | 状态 |
|---|---|---|---|---|
| agents | 2 | 0 | 2（收入根因分析、宽带退单原因稽核）| ✓ 用户数据 |
| skills | 11 | 至多 1（携号转网风险评估，`status=deprecated`）| 10+ | ⚠️ 同名记录已 deprecated，不影响业务，保留 |
| aip_scenes | 1 | 0 | 1（四川收入根因分析场景）| ✓ 用户数据 |
| prompt_templates | 0 | 0 | 0 | ✓ 删除无影响 |

seed 函数本身有 `if count > 0: return` 保护，存量数据不会被清理；本次仅删除「自动注入新数据」的能力。
