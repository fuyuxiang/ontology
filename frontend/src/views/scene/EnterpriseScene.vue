<template>
  <SceneView :config="config" />
</template>

<script setup lang="ts">
import SceneView from './SceneView.vue'

const config = {
  namespace: 's4',
  title: '政企指标根因分析',
  description: '面向联通政企业务，以客户群体、产品服务、项目合同、客户经理等为核心，支持自然语言查询与多维下钻根因识别',
  color: 'var(--semantic-600)',
  icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 17l4-4 3 3 4-5 4 4" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}
</script>
