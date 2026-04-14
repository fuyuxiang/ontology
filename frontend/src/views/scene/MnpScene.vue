<template>
  <SceneView :config="config" />
</template>

<script setup lang="ts">
import SceneView from './SceneView.vue'

const config = {
  namespace: 'mnp',
  title: '携号转网预警',
  description: '基于用户行为信号、家庭关系、常联系人网络，识别携转风险用户并触发精准维挽策略',
  color: 'var(--status-error)',
}
</script>
