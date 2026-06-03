# 本体平台 UI 设计文档索引

> 本目录包含本体管理平台所有页面的 UI 设计规范，供团队并行开发时参考。
> 
> 生成日期：2026-06-02

---

## 设计系统基准

| 文档 | 说明 |
|------|------|
| [00-design-system.md](./00-design-system.md) | 统一色彩、字体、间距、组件规范（所有页面开发前必读） |

---

## 01 工作台（Workspace）

| # | 页面 | 文档 | 路由 | 状态 |
|---|------|------|------|------|
| 1 | 业务总览 | [01-business-overview.md](./01-workspace/01-business-overview.md) | `/workspace/business` | 待开发 |
| 2 | 系统看板 | [02-system-dashboard.md](./01-workspace/02-system-dashboard.md) | `/dashboard` | 已有基础 |

---

## 02 数据集成（Data Integration）

| # | 页面 | 文档 | 路由 | 状态 |
|---|------|------|------|------|
| 3 | 数据接入 | [01-connections.md](./02-data-integration/01-connections.md) | `/data/connections` | 已实现 |
| 4 | 资产目录 | [02-assets.md](./02-data-integration/02-assets.md) | `/data/assets` | 已实现 |
| 5 | 数据管道 | [03-pipeline.md](./02-data-integration/03-pipeline.md) | `/data/pipeline` | 已实现 |
| 6 | 数据血缘 | [04-lineage.md](./02-data-integration/04-lineage.md) | `/data/lineage` | 已实现 |
| 7 | 数据质量 | [05-quality.md](./02-data-integration/05-quality.md) | `/data/quality` | 已实现 |

---

## 03 本体中心（Ontology Center）

| # | 页面 | 文档 | 路由 | 状态 |
|---|------|------|------|------|
| 8 | 工具构建 | [01-tool-builder.md](./03-ontology-center/01-tool-builder.md) | `/builder` | 已实现 |
| 9 | 模板构建 | [02-template-builder.md](./03-ontology-center/02-template-builder.md) | `/builder/template` | 已实现 |
| 10 | AI辅助构建 | [03-ai-builder.md](./03-ontology-center/03-ai-builder.md) | `/builder/ai` | 已实现 |
| 11 | 对象与关系管理 | [04-object-relation-mgmt.md](./03-ontology-center/04-object-relation-mgmt.md) | `/browser` | 已实现 |
| 12 | 映射管理 | [05-mapping-mgmt.md](./03-ontology-center/05-mapping-mgmt.md) | `/data/mapping` | 已实现 |
| 13 | 规则与函数管理 | [06-rule-function-mgmt.md](./03-ontology-center/06-rule-function-mgmt.md) | `/logic/rules` | 已实现 |
| 14 | 行动管理 | [07-action-mgmt.md](./03-ontology-center/07-action-mgmt.md) | `/logic/actions` | 已实现 |
| 15 | 图谱探索 | [08-graph-explorer.md](./03-ontology-center/08-graph-explorer.md) | `/studio` | 已实现 |
| 16 | 本体发布 | [09-publish.md](./03-ontology-center/09-publish.md) | `/ontology/publish` | 已实现 |
| 17 | 本体服务 | [10-service.md](./03-ontology-center/10-service.md) | `/service/api` | 已实现 |

---

## 04 智能体应用中心（Agent Center）

| # | 页面 | 文档 | 路由 | 状态 |
|---|------|------|------|------|
| 18 | 智能体管理 | [01-agent-manage.md](./04-agent-center/01-agent-manage.md) | `/agent/manage` | 已实现 |
| 19 | 技能管理 | [02-skill-manage.md](./04-agent-center/02-skill-manage.md) | `/agent/toolbox` | 待开发 |
| 20 | 任务编排 | [03-task-orchestration.md](./04-agent-center/03-task-orchestration.md) | `/agent/orchestration` | 待开发 |

---

## 05 场景中心（Scene Center）

| # | 页面 | 文档 | 路由 | 状态 |
|---|------|------|------|------|
| 21 | 场景中心主页 | [01-scene-hub.md](./05-scene-center/01-scene-hub.md) | `/scene` | 已实现 |
| 22 | 宽带退单稽核 | [02-broadband-audit.md](./05-scene-center/02-broadband-audit.md) | `/scene/broadband` | 已实现 |

---

## 06 运维与安全中心（Ops & Security）

| # | 页面 | 文档 | 路由 | 状态 |
|---|------|------|------|------|
| 23 | 运维监控 | [01-monitor.md](./06-ops-security/01-monitor.md) | `/ops/monitor` | 已有基础 |
| 24 | 日志与审计 | [02-log-audit.md](./06-ops-security/02-log-audit.md) | `/ops/log-audit` | 待开发 |
| 25 | 权限管理 | [03-permissions.md](./06-ops-security/03-permissions.md) | `/ops/permissions` | 待开发 |
| 26 | 系统配置 | [04-system-config.md](./06-ops-security/04-system-config.md) | `/ops/config` | 待开发 |

---

## 开发指引

### 启动前必读
1. 先完整阅读 `00-design-system.md` 了解色彩/字体/间距/组件的全局规范
2. 再阅读对应页面的详细设计文档
3. 所有组件基于 **Ant Design Vue 4.x**，图表基于 **AntV G6** / **Vue Flow**

### 风格一致性检查清单
- [ ] 色彩是否使用 CSS Token 变量（不硬编码）
- [ ] 字号是否遵循 7 级字体体系
- [ ] 间距是否基于 4px 网格
- [ ] 按钮高度统一 36px（标准）/ 28px（小）
- [ ] 卡片圆角统一 8px
- [ ] 表格行高统一 48px
- [ ] 页面内容区 padding 统一 24px / 32px
- [ ] 空状态/加载态/错误态三态齐全
- [ ] 深色模式变量覆盖完整
- [ ] 响应式 3 档断点适配

### 状态说明
| 标记 | 含义 |
|------|------|
| 已实现 | 有现成代码，文档描述现有设计并补充优化 |
| 已有基础 | 有部分实现，文档在其基础上扩展完整设计 |
| 待开发 | 全新设计，需要从零实现 |

---

*共计 26 个页面设计文档 + 1 份设计系统基准 = 27 份文档*
