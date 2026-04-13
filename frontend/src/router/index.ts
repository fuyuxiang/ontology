import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/ontology'
    },
    {
      path: '/ontology',
      name: 'ontology',
      component: () => import('../views/ontology/OntologyExplorer.vue'),
      meta: { title: '本体管理' }
    },
    {
      path: '/ontology/:id',
      name: 'ontology-detail',
      component: () => import('../views/detail/EntityDetail.vue'),
      meta: { title: '实体详情' }
    },
    {
      path: '/dataflow',
      name: 'dataflow',
      component: () => import('../views/dataflow/DataflowView.vue'),
      meta: { title: '关系画布' }
    },
    {
      path: '/logic',
      name: 'logic',
      component: () => import('../views/logic/LogicView.vue'),
      meta: { title: '业务逻辑' }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/dashboard/DashboardView.vue'),
      meta: { title: '数据看板' }
    },
    {
      path: '/copilot',
      name: 'copilot',
      component: () => import('../views/copilot/CopilotView.vue'),
      meta: { title: '智能对话' }
    }
  ]
})

router.afterEach((to) => {
  document.title = `${to.meta.title ?? '本体平台'} — 本体驱动智能策略平台`
})

export default router
