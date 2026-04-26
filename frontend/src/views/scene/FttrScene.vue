<template>
  <SceneView :config="config" />
</template>

<script setup lang="ts">
import SceneView from './SceneView.vue'

const config = {
  namespace: 'fttr',
  title: 'FTTR续约策划',
  description: '基于客户画像、订阅状态、流失风险模型，智能推荐续约策略，提升FTTR用户留存率',
  color: 'var(--dynamic-600)',
  icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>',
}
</script>
