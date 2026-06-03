# 系统看板（System Dashboard）实现设计

> 工作台 · 面向运维和管理员的系统健康监控页面

---

## 1. 概述

| 维度 | 说明 |
|------|------|
| 页面定位 | 平台运维监控中心，实时展示系统健康状态与关键性能指标 |
| 目标用户 | 系统管理员、运维工程师、技术负责人 |
| 路由路径 | `/dashboard` |
| 设计参考 | `docs/ui-design/01-workspace/02-system-dashboard.md` |

### 1.1 功能范围（全部 9 项）

| # | 功能点 | 优先级 | 数据来源 |
|---|--------|--------|---------|
| 1 | 服务健康状态概览 | P0 | 定时采集 → `t_service_metric` |
| 2 | 资源使用率仪表盘 | P0 | 实时 psutil + 定时落库 |
| 3 | 服务响应时间折线图 | P0 | 定时采集 → `t_service_metric` 历史查询 |
| 4 | 最近告警列表 | P1 | `t_alert` + WebSocket 推送 |
| 5 | 系统事件流 | P1 | EventBus → WebSocket 推送 |
| 6 | 本体数量统计 | P1 | 实时 count `OntologyEntity` 表 |
| 7 | 大模型调用量 | P1 | `t_llm_call_record` 24h 聚合 |
| 8 | Agent 活跃度 | P2 | `Agent` 表 + 执行记录 |
| 9 | 自动刷新控制 | P2 | 前端定时器开关 |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                      │
│  SystemDashboardView.vue                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │服务健康  │ │资源仪表盘│ │响应时间图│ │告警/事件 │   │
│  │卡片组    │ │环形图    │ │折线图    │ │列表/流   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│       ↕ REST(轮询)        ↕ REST      ↕ WebSocket      │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                        │
│  /api/v1/monitor/*  (REST)    /ws/monitor  (WebSocket)  │
│         ↕                            ↕                   │
│  ┌─────────────────────────────────────────────┐        │
│  │          services/monitor/                   │        │
│  │  collector.py   ws_manager.py   event_bus.py │        │
│  └─────────────────────────────────────────────┘        │
│         ↕                                               │
│  ┌─────────────────────────────────────────────┐        │
│  │  models/monitor.py                           │        │
│  │  ServiceMetric / LLMCallRecord / Alert       │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 2.1 数据流向

- **轮询类**（资源使用率、服务健康、本体数量、LLM调用量、Agent活跃度）：前端定时 GET → 后端查 DB/实时计算 → 返回
- **实时类**（告警、事件流）：后端 WebSocket 推送，前端长连接接收
- **采集类**（响应时间历史）：后端定时任务每 30s 采集 → 写 DB → 前端查历史

---

## 3. 数据模型

新建 `backend/app/models/monitor.py`。

### 3.1 服务响应时间历史 `t_service_metric`

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| service_name | VARCHAR(50) | 服务名，如 "后端API"、"数据库" |
| status | VARCHAR(20) | healthy / warning / unhealthy |
| response_ms | FLOAT | 响应时间(ms)，不可达时为 null |
| cpu_percent | FLOAT | 采集时刻的 CPU |
| memory_percent | FLOAT | 采集时刻的内存 |
| disk_percent | FLOAT | 采集时刻的磁盘 |
| collected_at | DATETIME | 采集时间，建索引 |

保留最近 7 天数据，定时清理。

### 3.2 LLM 调用记录 `t_llm_call_record`

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| caller_module | VARCHAR(50) | 调用方：copilot / agent / builder / rule_engine |
| model_name | VARCHAR(100) | 模型名 |
| prompt_tokens | INTEGER | 输入 token |
| completion_tokens | INTEGER | 输出 token |
| latency_ms | FLOAT | 调用耗时 |
| success | BOOLEAN | 是否成功 |
| created_at | DATETIME | 调用时间，建索引 |

### 3.3 告警记录 `t_alert`

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| level | VARCHAR(20) | critical / warning / info |
| service_name | VARCHAR(50) | 触发服务 |
| message | TEXT | 告警内容 |
| resolved | BOOLEAN | 是否已处理 |
| created_at | DATETIME | 告警时间 |
| resolved_at | DATETIME | 处理时间 |

---

## 4. 后端服务层

### 4.1 事件总线 `services/monitor/event_bus.py`

简单的异步事件总线，基于 `asyncio`：

```python
class EventBus:
    _subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable): ...
    async def emit(self, event_type: str, data: dict): ...
```

事件类型：
- `llm_call` — LLM 调用完成时触发，handler 写 `t_llm_call_record`
- `alert` — 告警触发时写 DB + 推 WebSocket
- `system_event` — 部署/配置变更/用户操作事件

接入方式：在现有 LLM 调用封装处加一行 `event_bus.emit("llm_call", {...})`，不改业务逻辑。

### 4.2 数据采集器 `services/monitor/collector.py`

定时任务，`asyncio.create_task` 在 lifespan 中启动：

| 任务 | 频率 | 逻辑 |
|------|------|------|
| `collect_service_metrics` | 30s | 遍历 10 个服务，ping 检测 + 读 psutil → 写 `t_service_metric` |
| `check_alerts` | 30s | 基于最新指标判定告警 → 写 `t_alert` + emit 事件 |
| `cleanup_old_data` | 1h | 删除 7 天前的 metric 和 30 天前的 alert |

### 4.3 10 个服务的健康检测方式

| 服务 | 检测方式 |
|------|---------|
| 后端API | `http://localhost:8001/health` |
| 数据库 | `SELECT 1` |
| 规则引擎 | 内存检测（同进程） |
| 函数运行时 | 内存检测 |
| Agent 服务 | 内存检测 |
| 本体引擎 | 内存检测（查 OntologyEntity count） |
| 图数据库 | Neo4j driver `session.run("RETURN 1")`，不可用时标记 unhealthy |
| 大模型网关 | `http://dashscope.aliyuncs.com` ping |
| MinIO | boto3 `head_bucket` |
| Redis | `redis.ping()`，未启用时标记 N/A |

### 4.4 WebSocket 管理器 `services/monitor/ws_manager.py`

```python
class MonitorWSManager:
    _connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket): ...
    async def disconnect(self, ws: WebSocket): ...
    async def broadcast(self, data: dict): ...
```

在 `main.py` 挂载 `/ws/monitor` 端点。心跳每 30s 发 ping，客户端 3 次未响应断开。

### 4.5 API 路由扩展 `api/v1/monitor.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/monitor/resources` | GET | 已有，保持 |
| `/monitor/services` | GET | 改为从 `t_service_metric` 读最新一条 |
| `/monitor/response-history` | GET | 新增，查 `t_service_metric` 最近 N 小时 |
| `/monitor/alerts` | GET | 新增，查 `t_alert`，支持筛选级别/状态 |
| `/monitor/alerts/{id}/resolve` | POST | 新增，标记告警已处理 |
| `/monitor/llm-stats` | GET | 新增，查 `t_llm_call_record` 24h 聚合 |
| `/monitor/ontology-stats` | GET | 新增，实时 count 各类本体 |
| `/monitor/overview` | GET | 改为聚合以上所有数据 |
| `/ws/monitor` | WS | 新增，WebSocket 端点 |

---

## 5. 前端实现

### 5.1 文件结构

```
frontend/src/
├── api/monitor.ts                          # 新增，监控 API 封装
├── composables/useMonitorWS.ts             # 新增，WebSocket 连接管理
├── views/dashboard/SystemDashboardView.vue # 重写
└── views/dashboard/components/             # 新增
    ├── ServiceHealthCards.vue              # 服务健康状态卡片组
    ├── ResourceGauges.vue                  # CPU/内存/磁盘环形图
    ├── ResponseTimeChart.vue               # 响应时间折线图
    ├── AlertTable.vue                      # 告警列表
    ├── EventStream.vue                     # 系统事件流
    ├── OntologyStats.vue                   # 本体数量统计
    ├── LLMCallStats.vue                    # 大模型调用量
    └── AgentActivity.vue                   # Agent 活跃度
```

### 5.2 页面布局

```
┌─────────────────────────────────────────────────────┐
│  系统看板              最后更新: 10:32:15  [30s ▾]  │
├─────────────────────────────────────────────────────┤
│  [后端API] [数据库] [规则引擎] [函数运行时] [Agent]  │
│  [本体引擎] [图数据库] [大模型网关] [MinIO] [Redis]  │
├──────────────────┬──────────────────────────────────┤
│  资源使用率 40%  │  服务响应时间 60%                │
│  [CPU][内存][磁盘]│  多折线图 + 时间范围切换         │
├──────────────────┴──────────────────────────────────┤
│  本体数量 33%    │  大模型调用量 33%  │ Agent 33%  │
├──────────────────┴──────────────────────────────────┤
│  最近告警 50%              │  系统事件流 50%         │
│  表格，最多20条            │  时间线，实时滚动       │
└─────────────────────────────────────────────────────┘
```

### 5.3 数据刷新策略

| 区域 | 方式 | 频率 |
|------|------|------|
| 服务健康 | REST 轮询 | 30s |
| 资源使用率 | REST 轮询 | 30s |
| 响应时间图 | REST 轮询追加 | 60s |
| 本体数量 | REST 轮询 | 60s |
| LLM 调用量 | REST 轮询 | 60s |
| Agent 活跃度 | REST 轮询 | 60s |
| 告警列表 | WebSocket 推送 | 实时 |
| 系统事件流 | WebSocket 推送 | 实时 |

### 5.4 技术选型

| 需求 | 方案 |
|------|------|
| 环形仪表盘 | ECharts gauge |
| 折线图 | ECharts line |
| 表格 | Ant Design Vue `a-table` |
| 标签/徽标 | `a-tag` / `a-badge` |
| 骨架屏 | `a-skeleton` |
| WebSocket | 原生 WebSocket + 自动重连 |
| 状态管理 | 组件内 `ref` + `onMounted` 轮询 |

### 5.5 深色模式

复用项目已有的 theme store，通过 CSS 变量切换。ECharts 图表通过 `theme` 参数适配。

---

## 6. 响应式适配

| 断点 | 服务健康栏 | 中间区域 | 底部区域 |
|------|-----------|----------|----------|
| >=1920px | 单行10项 | 左40% + 右60% | 左50% + 右50% |
| 1440-1919px | 单行10项（紧凑） | 左40% + 右60% | 左50% + 右50% |
| <1280px | 两行各5项 | 上下堆叠 | 上下堆叠 |

---

## 7. 新增文件清单

### 后端

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/models/monitor.py` | 新增 | ORM 模型：ServiceMetric、LLMCallRecord、Alert |
| `backend/app/repositories/monitor_repo.py` | 新增 | 数据访问层 |
| `backend/app/services/monitor/__init__.py` | 新增 | 包初始化 |
| `backend/app/services/monitor/event_bus.py` | 新增 | 异步事件总线 |
| `backend/app/services/monitor/collector.py` | 新增 | 定时采集器 |
| `backend/app/services/monitor/ws_manager.py` | 新增 | WebSocket 管理器 |
| `backend/app/schemas/monitor.py` | 新增 | Pydantic 请求/响应模型 |

### 前端

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/api/monitor.ts` | 新增 | 监控 API 封装 |
| `frontend/src/composables/useMonitorWS.ts` | 新增 | WebSocket composable |
| `frontend/src/views/dashboard/SystemDashboardView.vue` | 重写 | 替换 PlaceholderView |
| `frontend/src/views/dashboard/components/ServiceHealthCards.vue` | 新增 | 服务健康卡片 |
| `frontend/src/views/dashboard/components/ResourceGauges.vue` | 新增 | 资源环形图 |
| `frontend/src/views/dashboard/components/ResponseTimeChart.vue` | 新增 | 响应时间折线图 |
| `frontend/src/views/dashboard/components/AlertTable.vue` | 新增 | 告警列表 |
| `frontend/src/views/dashboard/components/EventStream.vue` | 新增 | 事件流 |
| `frontend/src/views/dashboard/components/OntologyStats.vue` | 新增 | 本体统计 |
| `frontend/src/views/dashboard/components/LLMCallStats.vue` | 新增 | LLM 调用量 |
| `frontend/src/views/dashboard/components/AgentActivity.vue` | 新增 | Agent 活跃度 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `backend/app/main.py` | lifespan 中启动采集器 + 挂载 WebSocket 端点 |
| `backend/app/api/v1/monitor.py` | 扩展路由，新增 6 个端点 |
| `backend/app/models/__init__.py` | 注册新模型 |
| `backend/app/database.py` | 确保新表 create_all |

---

## 8. 实现顺序

1. **数据模型** — 新建 `models/monitor.py`，注册到 `__init__.py`
2. **事件总线** — `services/monitor/event_bus.py`
3. **WebSocket 管理器** — `services/monitor/ws_manager.py`
4. **数据采集器** — `services/monitor/collector.py`
5. **API 路由** — 扩展 `api/v1/monitor.py`
6. **main.py 接入** — lifespan 启动采集器 + 挂载 WS
7. **前端 API 层** — `api/monitor.ts` + `composables/useMonitorWS.ts`
8. **前端组件** — 8 个子组件按顺序实现
9. **主页面组装** — `SystemDashboardView.vue` 组合所有组件
