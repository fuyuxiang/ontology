import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/browser',
      component: () => import('../views/browser/OntologyBrowser.vue'),
      meta: { title: '本体浏览器' },
      children: [
        {
          path: '',
          name: 'browser-objects',
          component: () => import('../views/ontology/OntologyExplorer.vue'),
          meta: { title: '本体管理' }
        },
        {
          path: 'graph',
          name: 'browser-graph',
          component: () => import('../views/dataflow/DataflowView.vue'),
          meta: { title: '关系画布' }
        },
        {
          path: 'rules',
          name: 'browser-rules',
          component: () => import('../views/logic/LogicView.vue'),
          meta: { title: '业务规则' }
        },
      ]
    },
    {
      path: '/ontology/:id',
      name: 'ontology-detail',
      component: () => import('../views/detail/EntityDetail.vue'),
      meta: { title: '实体详情' }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/dashboard/DashboardView.vue'),
      meta: { title: '系统总览' }
    },
    {
      path: '/datasource',
      name: 'datasource',
      component: () => import('../views/datasource/DataSourceView.vue'),
      meta: { title: '数据源管理' }
    },
    {
      path: '/copilot/:appId?',
      name: 'copilot',
      component: () => import('../views/copilot/CopilotView.vue'),
      meta: { title: '智能对话' }
    },
    {
      path: '/scene',
      name: 'scene-hub',
      component: () => import('../views/scene/SceneHub.vue'),
      meta: { title: '业务场景模拟' }
    },
    {
      path: '/scene/fttr',
      name: 'scene-fttr',
      component: () => import('../views/scene/FttrScene.vue'),
      meta: { title: 'FTTR续约策划' }
    },
    {
      path: '/scene/broadband',
      name: 'scene-broadband',
      component: () => import('../views/scene/BroadbandScene.vue'),
      meta: { title: '宽带退单稽核' }
    },
    {
      path: '/scene/broadband/stats',
      name: 'scene-broadband-stats',
      component: () => import('../views/scene/BroadbandStats.vue'),
      meta: { title: '退单稽核统计' }
    },
    {
      path: '/scene/broadband/inbox',
      name: 'scene-broadband-inbox',
      component: () => import('../views/scene/BroadbandInbox.vue'),
      meta: { title: '智能收件箱' }
    },
    {
      path: '/scene/broadband/:id',
      name: 'scene-broadband-detail',
      component: () => import('../views/scene/BroadbandDetail.vue'),
      meta: { title: '退单详情' }
    },
    {
      path: '/scene/enterprise',
      name: 'scene-enterprise',
      component: () => import('../views/scene/EnterpriseScene.vue'),
      meta: { title: '政企根因分析' }
    },
    {
      path: '/scene/mnp',
      name: 'scene-mnp',
      component: () => import('../views/scene/MnpWorkbench.vue'),
      meta: { title: '携号转网预警' }
    },
    {
      path: '/aip/lowcode',
      name: 'aip-lowcode',
      component: () => import('../views/aip/LowCodeBuilder.vue'),
      meta: { title: '低代码平台' }
    },
    {
      path: '/harness',
      name: 'harness',
      component: () => import('../views/harness/HarnessView.vue'),
      meta: { title: '智能编排中心' }
    }
  ]
})

router.afterEach((to) => {
  document.title = `${to.meta.title ?? '元枢Ontology'} — 元枢Ontology`
})

export default router
