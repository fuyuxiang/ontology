# BONC 本体驱动智能策略平台 — 长期记忆

## 项目概况
- 工作区：`/Users/fuyuxiang/Desktop/palantir/bonc-ontology`
- 前端框架：Vue 3 + TypeScript + Vite（无 React，纯 Vue）
- 状态管理：Pinia；路由：Vue Router 4
- 设计体系来源：`/Users/fuyuxiang/Desktop/UI-DESIGN-SYSTEM-界面设计体系.md`
- 前后端分离，后端暂不开发，保留路由占位

## 前端目录结构（frontend/src）
```
styles/         tokens.css（CSS 变量）+ global.css（工具类）
components/common/  AppSidebar、AppTopbar、EntityCard、OntologyBreadcrumb、TierBadge
views/
  ontology/     OntologyExplorer.vue（本体管理主页）
  detail/       EntityDetail.vue（实体详情页 /ontology/:id）
  dashboard/    DashboardView.vue（数据看板）
  copilot/      CopilotView.vue（智能副驾）
  PlaceholderView.vue（数据流/业务逻辑占位）
router/index.ts store/theme.ts  main.ts  App.vue
```

## 路由表
| 路径 | 页面 | 状态 |
|------|------|------|
| `/ontology` | 本体管理 | 完成 |
| `/ontology/:id` | 实体详情 | 完成 |
| `/dashboard` | 数据看板 | 完成 |
| `/copilot` | 智能副驾 | 完成 |
| `/dataflow` | 数据流 | 占位（待后端） |
| `/logic` | 业务逻辑 | 占位（待后端） |

## 设计令牌关键约定
- Tier1 蓝 `#4c6ef5`，Tier2 紫 `#7950f2`，Tier3 绿 `#20c997`
- Semantic（结构蓝）/ Kinetic（琥珀橙）/ Dynamic（翠绿青）三套品牌色
- 深色模式通过 `[data-theme="dark"]` 切换，由 `store/theme.ts` 管理

## 开发服务器
- 端口：5173，命令：`cd frontend && npm run dev`
