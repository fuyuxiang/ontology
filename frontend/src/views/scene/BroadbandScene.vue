<template>
  <SceneView :config="config" />
</template>

<script setup lang="ts">
import SceneView from './SceneView.vue'

const config = {
  namespace: 's1',
  title: '宽带装机退单稽核',
  description: '基于订单、派单、录音、地址库等多源数据，通过本体规则与大模型协同，自动判断退单原因合理性',
  color: 'var(--kinetic-600)',
  icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="9" stroke="#fff" stroke-width="2"/></svg>',
}
</script>
