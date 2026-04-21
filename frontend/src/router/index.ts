import { createRouter, createWebHistory } from 'vue-router'

const Placeholder = () => import('../views/common/PlaceholderPage.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'), meta: { title: '登录', public: true } },

    // 工作台
    { path: '/dashboard', name: 'dashboard', component: () => import('../views/dashboard/DashboardView.vue'), meta: { title: '平台总览' } },
    { path: '/todo', name: 'todo', component: Placeholder, meta: { title: '我的待办' } },
    { path: '/changes', name: 'changes', component: Placeholder, meta: { title: '最近变更' } },

    // 本体资产
    {
      path: '/browser',
      component: () => import('../views/browser/OntologyBrowser.vue'),
      meta: { title: '本体目录' },
      children: [
        { path: '', name: 'browser-objects', component: () => import('../views/ontology/OntologyExplorer.vue'), meta: { title: '本体目录' } },
        { path: 'graph', name: 'browser-graph', component: () => import('../views/dataflow/DataflowView.vue'), meta: { title: '关系图谱' } },
        { path: 'rules', name: 'browser-rules', component: () => import('../views/logic/LogicView.vue'), meta: { title: '业务规则' } },
      ]
    },
    { path: '/search', name: 'search', component: Placeholder, meta: { title: '对象检索' } },
    { path: '/ontology/:id', name: 'ontology-detail', component: () => import('../views/detail/EntityDetail.vue'), meta: { title: '实体详情' } },

    // 本体建模
    { path: '/modeling/attributes', name: 'modeling-attributes', component: Placeholder, meta: { title: '属性管理' } },
    { path: '/modeling/actions', name: 'modeling-actions', component: Placeholder, meta: { title: '动作管理' } },
    { path: '/modeling/import-export', name: 'modeling-io', component: Placeholder, meta: { title: '模型导入导出' } },

    // 数据接入
    { path: '/datasource', name: 'datasource', component: () => import('../views/datasource/DataSourceView.vue'), meta: { title: '数据源' } },
    { path: '/knowledge', name: 'knowledge', component: () => import('../views/knowledge/KnowledgeView.vue'), meta: { title: '多模态知识库' } },
    { path: '/data/mapping', name: 'data-mapping', component: Placeholder, meta: { title: '本体映射' } },
    { path: '/data/resolution', name: 'data-resolution', component: Placeholder, meta: { title: '实体解析' } },
    { path: '/data/sync', name: 'data-sync', component: Placeholder, meta: { title: '同步任务' } },
    { path: '/data/lineage', name: 'data-lineage', component: Placeholder, meta: { title: '血缘分析' } },
    { path: '/data/quality', name: 'data-quality', component: Placeholder, meta: { title: '质量监控' } },

    // 智能编排
    { path: '/orchestration/semantic', name: 'orch-semantic', component: Placeholder, meta: { title: '语义封装' } },
    { path: '/orchestration/prompts', name: 'orch-prompts', component: Placeholder, meta: { title: 'Prompt模板' } },
    { path: '/harness', name: 'harness', component: () => import('../views/harness/HarnessView.vue'), meta: { title: '场景编排' } },
    { path: '/orchestration/models', name: 'orch-models', component: Placeholder, meta: { title: '模型管理' } },
    { path: '/aip/lowcode', name: 'aip-lowcode', component: Placeholder, meta: { title: '低代码平台' } },

    // 智能应用
    { path: '/copilot', name: 'copilot', component: () => import('../views/copilot/CopilotView.vue'), meta: { title: '知识问答' } },
    { path: '/scene', name: 'scene-hub', component: () => import('../views/scene/SceneHub.vue'), meta: { title: '场景验证' } },
    { path: '/scene/fttr', name: 'scene-fttr', component: () => import('../views/scene/FttrScene.vue'), meta: { title: 'FTTR续约策划' } },
    { path: '/scene/broadband', name: 'scene-broadband', component: () => import('../views/scene/BroadbandScene.vue'), meta: { title: '宽带退单稽核' } },
    { path: '/scene/broadband/stats', name: 'scene-broadband-stats', component: () => import('../views/scene/BroadbandStats.vue'), meta: { title: '退单稽核统计' } },
    { path: '/scene/broadband/inbox', name: 'scene-broadband-inbox', component: () => import('../views/scene/BroadbandInbox.vue'), meta: { title: '智能收件箱' } },
    { path: '/scene/broadband/:id', name: 'scene-broadband-detail', component: () => import('../views/scene/BroadbandDetail.vue'), meta: { title: '退单详情' } },
    { path: '/scene/enterprise', name: 'scene-enterprise', component: () => import('../views/scene/EnterpriseScene.vue'), meta: { title: '政企根因分析' } },
    { path: '/scene/mnp', name: 'scene-mnp', component: () => import('../views/scene/MnpWorkbench.vue'), meta: { title: '携号转网预警' } },
    { path: '/app/alerts', name: 'app-alerts', component: Placeholder, meta: { title: '订阅预警' } },
    { path: '/app/api', name: 'app-api', component: Placeholder, meta: { title: 'API开放' } },

    // 治理中心
    { path: '/governance/versions', name: 'gov-versions', component: Placeholder, meta: { title: '版本管理' } },
    { path: '/governance/permissions', name: 'gov-permissions', component: Placeholder, meta: { title: '权限控制' } },
    { path: '/governance/reviews', name: 'gov-reviews', component: Placeholder, meta: { title: '变更评审' } },
    { path: '/governance/releases', name: 'gov-releases', component: Placeholder, meta: { title: '发布中心' } },
    { path: '/governance/audit', name: 'gov-audit', component: Placeholder, meta: { title: '审计日志' } },
    { path: '/governance/glossary', name: 'gov-glossary', component: Placeholder, meta: { title: '术语标准' } },
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
