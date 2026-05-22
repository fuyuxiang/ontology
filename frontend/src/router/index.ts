import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'), meta: { title: '登录', public: true } },

    // 工作台
    { path: '/dashboard', name: 'dashboard', component: () => import('../views/dashboard/DashboardView.vue'), meta: { title: '平台总览' } },
    { path: '/todo', name: 'todo', component: () => import('../views/todo/TodoView.vue'), meta: { title: '我的待办' } },

    // 本体中心
    {
      path: '/browser',
      component: () => import('../views/browser/OntologyBrowser.vue'),
      meta: { title: '本体目录' },
      children: [
        { path: '', name: 'browser-objects', component: () => import('../views/ontology/OntologyExplorer.vue'), meta: { title: '本体目录' } },
      ]
    },
    { path: '/browser/graph', name: 'browser-graph', component: () => import('../views/dataflow/DataflowView.vue'), meta: { title: '本体图谱' } },
    { path: '/studio', name: 'studio', component: () => import('../views/studio/OntologyStudio.vue'), meta: { title: '本体工作室' } },
    { path: '/builder', name: 'ontology-builder', component: () => import('../views/builder/OntologyBuilderView.vue'), meta: { title: '本体构建器' } },
    { path: '/ontology/publish', name: 'ontology-publish', component: () => import('../views/ontology/OntologyPublishView.vue'), meta: { title: '本体发布' } },
    { path: '/ontology/create', name: 'ontology-create', component: () => import('../views/ontology/EntityCreateView.vue'), meta: { title: '新建本体对象' } },
    { path: '/ontology/:id', name: 'ontology-detail', component: () => import('../views/detail/EntityDetail.vue'), meta: { title: '实体详情' } },

    // 数据中心
    { path: '/datasource', name: 'datasource', component: () => import('../views/datasource/DataWorkshopView.vue'), meta: { title: '数据工坊' } },
    { path: '/data/workshop', name: 'data-workshop', component: () => import('../views/datasource/DataWorkshopView.vue'), meta: { title: '数据工坊' } },
    { path: '/data/mapping', name: 'data-mapping', component: () => import('../views/mapping/MappingView.vue'), meta: { title: '本体映射' } },
    { path: '/data/resolution', name: 'data-resolution', component: () => import('../views/resolution/ResolutionView.vue'), meta: { title: '实体解析' } },

    // 逻辑中心
    { path: '/logic/actions', name: 'logic-actions', component: () => import('../views/logic/ActionsView.vue'), meta: { title: 'Actions 管理' } },
    { path: '/logic/functions', name: 'logic-functions', component: () => import('../views/logic/FunctionsView.vue'), meta: { title: 'Functions 管理' } },
    { path: '/logic/rules', name: 'logic-rules', component: () => import('../views/logic/LogicView.vue'), meta: { title: 'Rules 管理' } },
    { path: '/logic/skills', name: 'logic-skills', component: () => import('../views/logic/SkillsView.vue'), meta: { title: 'Skills 管理' } },
    { path: '/logic/documents', name: 'logic-documents', component: () => import('../views/logic/DocumentsView.vue'), meta: { title: '业务文档库' } },

    // 本体服务
    { path: '/service/api', name: 'service-api', component: () => import('../views/service/ApiServiceView.vue'), meta: { title: 'API 服务' } },
    { path: '/service/osdk', name: 'service-osdk', component: () => import('../views/service/OsdkView.vue'), meta: { title: 'OSDK 生成' } },
    { path: '/service/agent', name: 'service-agent', component: () => import('../views/service/AgentServiceView.vue'), meta: { title: 'Agent 交互' } },
    { path: '/service/agent/:id', name: 'service-agent-detail', component: () => import('../views/agents/AgentDetailView.vue'), meta: { title: '智能体详情' } },
    { path: '/service/workflow', name: 'service-workflow', component: () => import('../views/harness/HarnessView.vue'), meta: { title: '流程编排' } },
    { path: '/harness', name: 'ontology-harness', component: () => import('../views/harness/OntologyHarnessView.vue'), meta: { title: '本体试车场' } },

    // AIP 场景平台
    { path: '/aip', name: 'aip-platform', component: () => import('../views/aip/AipPlatformView.vue'), meta: { title: 'AIP 场景平台' } },

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
    { path: '/ops/traces', name: 'ops-traces', component: () => import('../views/ops/AgentTracesView.vue'), meta: { title: '运行追踪' } },

    // 系统设置
    { path: '/settings/models', name: 'settings-models', component: () => import('../views/models/ModelManageView.vue'), meta: { title: '模型管理' } },
    { path: '/settings/monitor', name: 'settings-monitor', component: () => import('../views/settings/MonitorView.vue'), meta: { title: '运维监控' } },
    { path: '/settings/general', name: 'settings-general', component: () => import('../views/governance/GovernanceView.vue'), meta: { title: '系统配置' } },
    { path: '/governance/audit', name: 'gov-audit', component: () => import('../views/governance/AuditLogView.vue'), meta: { title: '权限审计' } },
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
