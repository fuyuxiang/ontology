<template>
  <div class="wf-node" :class="[`wf-node--${nodeType}`, stateClass]">
    <Handle type="target" :position="Position.Left" class="wf-handle wf-handle--in" />

    <div class="wf-node__header">
      <span class="wf-node__icon" v-html="nodeIcon"></span>
      <span class="wf-node__title">{{ nodeLabel }}</span>
      <span class="wf-node__state-dot" :class="`wf-node__state-dot--${execState}`"></span>
    </div>

    <div class="wf-node__body">
      <div class="wf-node__name">{{ data.label || nodeLabel }}</div>
      <div class="wf-node__desc" v-if="data.description">{{ data.description }}</div>
      <div class="wf-node__result" v-if="data.result">{{ data.result }}</div>
    </div>

    <Handle type="source" :position="Position.Right" class="wf-handle wf-handle--out" />
    <Handle v-if="nodeType === 'condition'" type="source" :position="Position.Bottom"
      id="false" class="wf-handle wf-handle--out wf-handle--bottom" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  id: string
  type: string
  data: Record<string, any>
  selected?: boolean
}>()

const nodeType = computed(() => props.type || 'ontology-query')

const NODE_META: Record<string, { label: string; icon: string; color: string }> = {
  'ontology-query': {
    label: '本体查询',
    color: '#3b82f6',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  },
  'datasource': {
    label: '数据源连接',
    color: '#8b5cf6',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>`,
  },
  'rule-engine': {
    label: '规则引擎',
    color: '#f59e0b',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="13" cy="10" r="2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  },
  'llm-inference': {
    label: '大模型推理',
    color: '#10b981',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  },
  'ml-model': {
    label: '预测模型',
    color: '#06b6d4',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 7l3 3 2-4 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  'write-back': {
    label: '结果写回',
    color: '#64748b',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v8M5 8l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 13h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  },
  'notification': {
    label: '通知触达',
    color: '#ec4899',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2a5 5 0 015 5v2l1 2H2l1-2V7a5 5 0 015-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6.5 13a1.5 1.5 0 003 0" stroke="currentColor" stroke-width="1.5"/></svg>`,
  },
  'human-approval': {
    label: '人工审批',
    color: '#f97316',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M11 9l1.5 1.5L15 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  'condition': {
    label: '条件判断',
    color: '#a855f7',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  },
  'loop': {
    label: '遍历列表',
    color: '#0ea5e9',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 8a5 5 0 019.9-1M13 8a5 5 0 01-9.9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M12 4l1 3-3 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  'merge': {
    label: '合并分支',
    color: '#84cc16',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 3v4l4 3 4-3V3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
}

const meta = computed(() => NODE_META[nodeType.value] || NODE_META['ontology-query'])
const nodeLabel = computed(() => meta.value.label)
const nodeIcon = computed(() => meta.value.icon)
const execState = computed(() => props.data.execState || 'pending')

const stateClass = computed(() => {
  const s = []
  if (props.selected) s.push('wf-node--selected')
  if (execState.value === 'running') s.push('wf-node--running')
  if (execState.value === 'done') s.push('wf-node--done')
  if (execState.value === 'error') s.push('wf-node--error')
  return s
})
</script>

<style scoped>
.wf-node {
  min-width: 160px; max-width: 200px;
  background: #1e293b;
  border: 1.5px solid #334155;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,.4);
  cursor: pointer;
  transition: box-shadow .15s, border-color .15s;
  position: relative;
}
.wf-node:hover { box-shadow: 0 4px 20px rgba(0,0,0,.5); border-color: #475569; }
.wf-node--selected { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.25); }
.wf-node--running { border-color: #f59e0b; animation: wf-pulse 1.2s ease-in-out infinite; }
.wf-node--done { border-color: #10b981; }
.wf-node--error { border-color: #ef4444; }

@keyframes wf-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245,158,11,.4); }
  50% { box-shadow: 0 0 0 6px rgba(245,158,11,0); }
}

.wf-node__header {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px 6px;
  border-bottom: 1px solid #334155;
}
.wf-node__icon { width: 14px; height: 14px; flex-shrink: 0; color: v-bind('meta.color'); display: flex; }
.wf-node__title { font-size: 10px; font-weight: 600; color: #64748b; flex: 1; text-transform: uppercase; letter-spacing: .04em; }
.wf-node__state-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; background: #334155; }
.wf-node__state-dot--running { background: #f59e0b; }
.wf-node__state-dot--done { background: #10b981; }
.wf-node__state-dot--error { background: #ef4444; }

.wf-node__body { padding: 6px 10px 8px; }
.wf-node__name { font-size: 12px; font-weight: 600; color: #e2e8f0; }
.wf-node__desc { font-size: 10px; color: #475569; margin-top: 2px; }
.wf-node__result {
  font-size: 10px; color: #4ade80; margin-top: 4px;
  padding: 3px 6px; background: #052e16; border-radius: 4px;
}

.wf-handle {
  width: 10px; height: 10px;
  background: #1e293b; border: 2px solid #475569; border-radius: 50%;
  transition: border-color .15s;
}
.wf-handle:hover { border-color: #6366f1; }
.wf-handle--in { left: -6px; }
.wf-handle--out { right: -6px; }
.wf-handle--bottom { bottom: -6px; right: 50%; transform: translateX(50%); }
</style>
