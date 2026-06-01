import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'), meta: { title: '登录', public: true } },

    // 工作台
    { path: '/dashboard', name: 'dashboard', component: () => import('../views/dashboard/DashboardView.vue'), meta: { title: '平台总览' } },
    { path: '/workspace/business', name: 'workspace-business', component: () => import('../views/workspace/BusinessOverviewView.vue'), meta: { title: '业务总览' } },
    { path: '/todo', name: 'todo', component: () => import('../views/todo/TodoView.vue'), meta: { title: '我的待办' } },

    // 本体管理
    {
      path: '/browser',
      component: () => import('../views/browser/OntologyBrowser.vue'),
      meta: { title: '本体目录' },
      children: [
        { path: '', name: 'browser-objects', component: () => import('../views/ontology/OntologyExplorer.vue'), meta: { title: '本体目录' } },
      ]
    },
    { path: '/browser/graph', name: 'browser-graph', component: () => import('../views/dataflow/DataflowView.vue'), meta: { title: '本体图谱' } },
    { path: '/studio', name: 'studio', component: () => import('../views/studio/OntologyStudio.vue'), meta: { title: '本体全景' } },
    { path: '/builder', name: 'ontology-builder', component: () => import('../views/builder/OntologyBuilderView.vue'), meta: { title: '智能构建' } },
    { path: '/ontology/publish', name: 'ontology-publish', component: () => import('../views/ontology/OntologyPublishView.vue'), meta: { title: '本体发布' } },
    { path: '/ontology/create', name: 'ontology-create', component: () => import('../views/ontology/EntityCreateView.vue'), meta: { title: '新建本体对象' } },
    { path: '/ontology/:id', name: 'ontology-detail', component: () => import('../views/detail/EntityDetail.vue'), meta: { title: '实体详情' } },

    // 数据集成
    { path: '/datasource', redirect: '/data/connections' },
    { path: '/data/workshop', redirect: '/data/connections' },
    { path: '/data/ingest', redirect: '/data/connections' },

    // 新一代数据集成路由（M1）
    { path: '/data/connections', name: 'data-connections', component: () => import('../views/datasource/ConnectionsPage.vue'), meta: { title: '数据接入' } },
    { path: '/data/assets', name: 'data-assets', component: () => import('../views/datasource/AssetsPage.vue'), meta: { title: '资产目录' } },
    { path: '/data/audit', name: 'data-audit', component: () => import('../views/datasource/ExecutionAuditPage.vue'), meta: { title: '执行审计' } },

    // 旧路由（M1 期间保留兼容；M3 起 mapping/hydration 已迁出）
    { path: '/data/pipeline', name: 'data-pipeline', component: () => import('../views/datasource/pages/DataPipelinePage.vue'), meta: { title: '数据管道（已弃用）' } },
    { path: '/data/catalog', redirect: '/data/assets' },
    { path: '/data/lineage', name: 'data-lineage', component: () => import('../views/datasource/pages/DataLineagePage.vue'), meta: { title: '数据血缘' } },
    { path: '/data/quality', name: 'data-quality', component: () => import('../views/datasource/pages/DataQualityPage.vue'), meta: { title: '数据质量' } },
    { path: '/data/hydration', redirect: '/governance/pre-release' },
    { path: '/data/mapping', name: 'data-mapping', component: () => import('../views/mapping/MappingView.vue'), meta: { title: '本体映射（M3 起请到 ObjectType 详情页 · 绑定数据）' } },
    { path: '/data/resolution', name: 'data-resolution', component: () => import('../views/resolution/ResolutionView.vue'), meta: { title: '实体解析' } },

    // 治理（M3 新增 — 发布前关卡）
    { path: '/governance/pre-release', name: 'governance-pre-release', component: () => import('../views/governance/PreReleasePage.vue'), meta: { title: '治理 · 发布前关卡' } },
    { path: '/governance/permissions', name: 'governance-permissions', component: () => import('../views/governance/PermissionsView.vue'), meta: { title: '权限管理' } },
    { path: '/governance/impact', name: 'governance-impact', component: () => import('../views/governance/ImpactAnalysisView.vue'), meta: { title: '影响分析' } },

    // 逻辑中心
    { path: '/logic/actions', name: 'logic-actions', component: () => import('../views/logic/ActionsView.vue'), meta: { title: '行动管理' } },
    { path: '/logic/functions', name: 'logic-functions', component: () => import('../views/logic/FunctionsView.vue'), meta: { title: '函数管理' } },
    { path: '/logic/rules', name: 'logic-rules', component: () => import('../views/logic/LogicView.vue'), meta: { title: '规则管理' } },
    { path: '/logic/skills', name: 'logic-skills', component: () => import('../views/logic/SkillsView.vue'), meta: { title: 'Skills 管理' } },
    { path: '/logic/documents', name: 'logic-documents', component: () => import('../views/logic/DocumentsView.vue'), meta: { title: '业务文档库' } },

    // 本体服务
    { path: '/service/api', name: 'service-api', component: () => import('../views/service/ApiServiceView.vue'), meta: { title: '服务定义' } },
    { path: '/service/osdk', name: 'service-osdk', component: () => import('../views/service/OsdkView.vue'), meta: { title: 'API 与 OSDK' } },
    { path: '/service/agent', name: 'service-agent', component: () => import('../views/service/AgentServiceView.vue'), meta: { title: 'Agent 管理' } },
    { path: '/service/agent/:id', name: 'service-agent-detail', component: () => import('../views/agents/AgentDetailView.vue'), meta: { title: '智能体详情' } },
    { path: '/service/workflow', name: 'service-workflow', component: () => import('../views/harness/HarnessView.vue'), meta: { title: '流程编排' } },
    { path: '/service/monitor', name: 'service-monitor', component: () => import('../views/service/CallMonitorView.vue'), meta: { title: '调用监控' } },
    { path: '/harness', name: 'ontology-harness', component: () => import('../views/harness/OntologyHarnessView.vue'), meta: { title: '试车场' } },

    // AIP 场景平台
    { path: '/aip', name: 'aip-platform', component: () => import('../views/aip/AipPlatformView.vue'), meta: { title: '场景模板库' } },

    // 业务场景
    { path: '/scene', name: 'scene-hub', component: () => import('../views/scene/SceneHub.vue'), meta: { title: '场景总览' } },
    { path: '/scene/fttr', name: 'scene-fttr', component: () => import('../views/scene/FttrScene.vue'), meta: { title: 'FTTR续约策划' } },
    { path: '/scene/broadband', name: 'scene-broadband', component: () => import('../views/scene/BroadbandScene.vue'), meta: { title: '宽带退单稽核' } },
    { path: '/scene/broadband/stats', name: 'scene-broadband-stats', component: () => import('../views/scene/BroadbandStats.vue'), meta: { title: '退单稽核统计' } },
    { path: '/scene/broadband/inbox', name: 'scene-broadband-inbox', component: () => import('../views/scene/BroadbandInbox.vue'), meta: { title: '智能收件箱' } },
    { path: '/scene/broadband/:id', name: 'scene-broadband-detail', component: () => import('../views/scene/BroadbandDetail.vue'), meta: { title: '退单详情' } },
    { path: '/scene/enterprise', name: 'scene-enterprise', component: () => import('../views/scene/EnterpriseScene.vue'), meta: { title: '政企根因分析' } },
    { path: '/scene/mnp', name: 'scene-mnp', component: () => import('../views/scene/MnpWorkbench.vue'), meta: { title: '携号转网预警' } },

    // 运营观测
    { path: '/ops/evals', name: 'ops-evals', component: () => import('../views/ops/AgentEvalsView.vue'), meta: { title: 'Agent 评测' } },
    { path: '/ops/traces', name: 'ops-traces', component: () => import('../views/ops/AgentTracesView.vue'), meta: { title: '运行链路' } },

    // 系统设置
    { path: '/settings/models', name: 'settings-models', component: () => import('../views/models/ModelManageView.vue'), meta: { title: '模型配置' } },
    { path: '/settings/monitor', name: 'settings-monitor', component: () => import('../views/settings/MonitorView.vue'), meta: { title: '系统监控' } },
    { path: '/settings/general', name: 'settings-general', component: () => import('../views/governance/GovernanceView.vue'), meta: { title: '系统配置' } },
    { path: '/settings/tenants', name: 'settings-tenants', component: () => import('../views/settings/TenantsView.vue'), meta: { title: '租户管理' } },
    { path: '/governance/audit', name: 'gov-audit', component: () => import('../views/governance/OperationAuditView.vue'), meta: { title: '操作审计' } },
  ]
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  const token = localStorage.getItem('token')
  if (!token) return { name: 'login' }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title ?? '元枢Ontology'} — 元枢Ontology`
})

export default router
