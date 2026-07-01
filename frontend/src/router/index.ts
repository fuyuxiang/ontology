import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'), meta: { title: '登录', public: true } },

    // 工作台
    { path: '/workspace/business', name: 'workspace-business', component: () => import('../views/dashboard/DashboardView.vue'), meta: { title: '业务总览' } },
    { path: '/dashboard', name: 'dashboard', component: () => import('../views/dashboard/SystemDashboardView.vue'), meta: { title: '系统看版' } },

    // 数据集成
    { path: '/data/connections', name: 'data-connections', component: () => import('../views/datasource/ConnectionsPage.vue'), meta: { title: '数据接入' } },
    { path: '/data/assets', name: 'data-assets', component: () => import('../views/datasource/AssetsPage.vue'), meta: { title: '资产目录' } },

    // 本体中心 — 本体构建
    { path: '/builder', name: 'ontology-builder', component: () => import('../views/builder/OntologyBuilderView.vue'), meta: { title: '手动构建' } },
    { path: '/builder/template', name: 'ontology-builder-template', component: () => import('../views/builder/TemplateBuilderView.vue'), meta: { title: '模板构建' } },
    { path: '/builder/doc', name: 'ontology-builder-doc', component: () => import('../views/builder/DocBuilderView.vue'), meta: { title: '文档构建' } },
    { path: '/builder/ai', name: 'ontology-builder-ai', component: () => import('../views/builder/AiBuilderView.vue'), meta: { title: '资产构建' } },

    // 本体中心 — 本体管理
    {
      path: '/browser',
      component: () => import('../views/browser/OntologyBrowser.vue'),
      meta: { title: '对象与关系管理' },
      children: [
        { path: '', name: 'browser-objects', component: () => import('../views/ontology/OntologyExplorer.vue'), meta: { title: '对象与关系管理' } },
      ]
    },
    { path: '/data/mapping', name: 'data-mapping', component: () => import('../views/mapping/MappingView.vue'), meta: { title: '映射管理' } },
    { path: '/logic/rules', name: 'logic-rules', component: () => import('../views/logic/LogicView.vue'), meta: { title: '规则管理' } },
    { path: '/logic/functions', name: 'logic-functions', component: () => import('../views/logic/FunctionsView.vue'), meta: { title: '函数管理' } },
    { path: '/logic/actions', name: 'logic-actions', component: () => import('../views/logic/ActionsView.vue'), meta: { title: '行动管理' } },

    // 本体中心 — 本体探索
    { path: '/studio', name: 'studio', component: () => import('../views/studio/OntologyStudio.vue'), meta: { title: '本体探索' } },

    // 本体中心 — 本体发布
    { path: '/ontology/publish', name: 'ontology-publish', component: () => import('../views/ontology/OntologyPublishView.vue'), meta: { title: '本体发布' } },
    { path: '/ontology/version', redirect: '/ontology/publish' },

    // 本体中心 — 本体服务
    { path: '/service/api', name: 'service-api', component: () => import('../views/service/ApiServiceView.vue'), meta: { title: '本体服务' } },

    // 本体中心 — 辅助路由
    { path: '/ontology/create', name: 'ontology-create', component: () => import('../views/ontology/EntityCreateView.vue'), meta: { title: '新建本体对象' } },
    { path: '/ontology/:id', name: 'ontology-detail', component: () => import('../views/detail/EntityDetail.vue'), meta: { title: '实体详情' } },
    { path: '/browser/graph', name: 'browser-graph', component: () => import('../views/dataflow/DataflowView.vue'), meta: { title: '本体图谱' } },

    // 智能体应用中心
    { path: '/agent/manage', name: 'agent-manage', component: () => import('../views/service/AgentServiceView.vue'), meta: { title: '智能体管理' } },
    { path: '/agent/manage/new', name: 'agent-new', component: () => import('../views/agents/AgentDetailView.vue'), meta: { title: '新建智能体' } },
    { path: '/agent/manage/:id', name: 'agent-detail', component: () => import('../views/agents/AgentDetailView.vue'), meta: { title: '智能体详情' } },
    { path: '/agent/toolbox', name: 'agent-toolbox', component: () => import('../views/agents/skills/SkillListView.vue'), meta: { title: '技能管理' } },
    { path: '/agent/toolbox/create', name: 'skill-create', component: () => import('../views/agents/skills/SkillWizard.vue'), meta: { title: '创建技能' } },
    { path: '/agent/toolbox/:id', name: 'skill-detail', component: () => import('../views/agents/skills/SkillDetailView.vue'), meta: { title: '技能详情' } },
    { path: '/aip', name: 'aip-platform', component: () => import('../views/aip/AipPlatformView.vue'), meta: { title: '流程编排' } },

    // 运维与安全中心
    { path: '/ops/monitor', name: 'ops-monitor', component: () => import('../views/settings/MonitorView.vue'), meta: { title: '运维监控' } },
    { path: '/ops/log-audit', name: 'ops-log-audit', component: () => import('../views/ops/LogAuditView.vue'), meta: { title: '日志与审计' } },
    { path: '/ops/permissions', name: 'ops-permissions', component: () => import('../views/governance/PermissionsView.vue'), meta: { title: '权限管理' } },
    { path: '/ops/config', name: 'ops-config', component: () => import('../views/settings/SystemConfigView.vue'), meta: { title: '系统配置' } },
    { path: '/settings/models', name: 'settings-models', component: () => import('../views/models/ModelManageView.vue'), meta: { title: '模型配置' } },

    // 兼容旧路由
    { path: '/datasource', redirect: '/data/connections' },
    { path: '/data/workshop', redirect: '/data/connections' },
    { path: '/data/ingest', redirect: '/data/connections' },
    { path: '/data/catalog', redirect: '/data/assets' },
    { path: '/data/hydration', redirect: '/ontology/publish' },
    { path: '/service/agent', redirect: '/agent/manage' },
    { path: '/service/workflow', redirect: '/aip' },
    { path: '/harness', redirect: '/aip' },
    { path: '/settings/monitor', redirect: '/ops/monitor' },
    { path: '/settings/general', redirect: '/ops/config' },
    { path: '/governance/permissions', redirect: '/ops/permissions' },
    { path: '/governance/audit', redirect: '/ops/log-audit' },
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
