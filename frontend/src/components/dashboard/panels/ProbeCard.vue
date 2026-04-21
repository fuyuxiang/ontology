<template>
  <div class="probe-card glass-panel" :style="posStyle">
    <div class="probe__eyebrow">ENTITY · T{{ node.data.tier }}</div>
    <div class="probe__name">{{ node.data.label }}</div>
    <div class="probe__rows">
      <div class="probe__row"><span>关系</span><strong>{{ node.data.relationCount }}</strong></div>
      <div class="probe__row"><span>规则</span><strong>{{ node.data.ruleCount }}</strong></div>
      <div class="probe__row"><span>属性</span><strong>{{ node.data.attrCount }}</strong></div>
      <div class="probe__row"><span>动作</span><strong>{{ node.data.actionCount }}</strong></div>
    </div>
    <div class="probe__status">
      <span class="probe__dot" :class="`dot--${node.data.status}`"></span>
      {{ node.data.status }}
    </div>
    <div class="probe__health-lbl">HEALTH</div>
    <div class="probe__health-val">{{ health }}</div>
    <div class="probe__bar"><div class="probe__bar-fill" :style="{ width: health + '%' }"></div></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  node: { id: string; data: { label: string; tier: number; status: string; relationCount: number; ruleCount: number; attrCount: number; actionCount: number } }
  x: number
  y: number
}>()

const health = computed(() => {
  const base = props.node.data.status === 'active' ? 70 : props.node.data.status === 'warning' ? 45 : 20
  return Math.min(100, base + props.node.data.relationCount * 3 + props.node.data.ruleCount * 2)
})

const posStyle = computed(() => ({
  left: (props.x + 16) + 'px',
  top: (props.y - 60) + 'px',
}))
</script>

<style scoped>
.glass-panel {
  position: absolute;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  color: var(--neutral-300);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 14px;
  pointer-events: auto;
  z-index: 10;
}
.probe-card {
  position: fixed;
  width: 160px;
  padding: 12px 14px;
  z-index: 100;
  pointer-events: none;
  animation: probeIn .15s ease-out;
}
@keyframes probeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.probe__eyebrow { font-size: var(--text-caption-upper-size); font-weight: 800; letter-spacing: .1em; color: var(--neutral-700); text-transform: uppercase; }
.probe__name { font-size: var(--text-body-size); font-weight: 700; color: var(--neutral-300); margin: 3px 0 8px; }
.probe__rows { display: flex; flex-direction: column; gap: 3px; margin-bottom: 8px; }
.probe__row { display: flex; justify-content: space-between; font-size: var(--text-caption-size); }
.probe__row span { color: var(--neutral-500); }
.probe__row strong { color: var(--neutral-400); }
.probe__status { display: flex; align-items: center; gap: 5px; font-size: var(--text-caption-upper-size); color: var(--neutral-500); margin-bottom: 8px; }
.probe__dot { width: 6px; height: 6px; border-radius: 50%; }
.dot--active { background: var(--dynamic-500); }
.dot--warning { background: var(--kinetic-500); }
.dot--error { background: var(--status-error); }
.probe__health-lbl { font-size: var(--text-caption-upper-size); font-weight: 700; letter-spacing: .08em; color: var(--neutral-700); }
.probe__health-val { font-size: var(--text-h2-size); font-weight: 800; color: var(--kinetic-500); margin: 2px 0 4px; }
.probe__bar { height: 4px; background: rgba(241,245,249,.1); border-radius: 2px; overflow: hidden; }
.probe__bar-fill { height: 100%; background: linear-gradient(90deg, #10B981, #F59F00); border-radius: 2px; transition: width .4s ease; }
</style>
