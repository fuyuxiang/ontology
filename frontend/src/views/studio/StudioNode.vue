<template>
  <div class="studio-node" :class="[`studio-node--t${data.tier}`, { 'studio-node--selected': selected }]" :style="cssVars">
    <Handle type="target" :position="Position.Left" class="studio-node__handle" />

    <div class="studio-node__body">
      <div class="studio-node__name">{{ data.displayName }}</div>
      <div class="studio-node__en">{{ data.apiName }}</div>
    </div>

    <div class="studio-node__badges" v-if="data.showAbox || data.showRbox || data.instanceCount > 0">
      <span v-if="data.instanceCount > 0" class="studio-node__badge studio-node__badge--abox">
        {{ formatCount(data.instanceCount) }}
      </span>
      <span v-if="data.showRbox" class="studio-node__badge studio-node__badge--rbox">
        R{{ data.ruleCount }}
      </span>
    </div>

    <Handle type="source" :position="Position.Right" class="studio-node__handle studio-node__handle--source" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

interface NodeData {
  apiName: string
  displayName: string
  tier: 1 | 2 | 3
  color: string
  instanceCount: number
  ruleCount: number
  propCount: number
  showAbox: boolean
  showRbox: boolean
}

const props = defineProps<{
  data: NodeData
  selected?: boolean
}>()

const cssVars = computed(() => ({
  '--tc': props.data.color,
  '--tc-light': props.data.color + '18',
  '--tc-glow': props.data.color + '40',
}))

function formatCount(n: number): string {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}
</script>

<style scoped>
.studio-node {
  position: relative;
  min-width: 130px;
  max-width: 180px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff;
  border: 2px solid var(--tc);
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: all 0.18s;
}

.studio-node:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0,0,0,0.1), 0 0 0 3px var(--tc-glow);
}
.studio-node--selected {
  box-shadow: 0 4px 16px var(--tc-glow), 0 0 0 4px var(--tc-light);
}

.studio-node__body { flex: 1; min-width: 0; }
.studio-node__name {
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.3;
}
.studio-node__en {
  font-size: 9px;
  color: #94a3b8;
  font-family: monospace;
  margin-top: 2px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.studio-node__badges {
  display: flex;
  gap: 4px;
  margin-top: 2px;
  padding-top: 4px;
  border-top: 1px solid #f1f5f9;
}
.studio-node__badge {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
}
.studio-node__badge--abox { background: #ecfdf5; color: #047857; }
.studio-node__badge--rbox { background: #fef2f2; color: #b91c1c; }

.studio-node__handle {
  width: 6px;
  height: 6px;
  background: var(--tc);
  border: 1.5px solid #fff;
  border-radius: 50%;
}
.studio-node__handle--source { background: var(--tc); }
</style>
