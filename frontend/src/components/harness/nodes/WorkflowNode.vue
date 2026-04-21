<template>
  <div class="wf-node" :class="[`wf-node--${nodeType}`, stateClass]">
    <Handle type="target" :position="Position.Left" class="wf-handle wf-handle--in" />

    <!-- Colored top bar -->
    <div class="wf-node__topbar" :style="{ background: nodeGradient }"></div>

    <!-- Header -->
    <div class="wf-node__header">
      <div class="wf-node__icon-wrap" :style="{ background: nodeGradient }">
        <span class="wf-node__icon" v-html="nodeIcon"></span>
      </div>
      <div class="wf-node__header-info">
        <span class="wf-node__type-label">{{ nodeLabel }}</span>
        <span class="wf-node__name">{{ data.label || nodeLabel }}</span>
      </div>
      <div class="wf-node__state-badge" :class="`wf-node__state-badge--${execState}`">
        <span class="wf-node__state-dot"></span>
        <span class="wf-node__state-text">{{ stateLabel }}</span>
      </div>
    </div>

    <!-- Body -->
    <div class="wf-node__body" v-if="data.description || data.result || bodyExtra">
      <div class="wf-node__desc" v-if="data.description">{{ data.description }}</div>
      <div class="wf-node__extra" v-if="bodyExtra">
        <span class="wf-node__extra-key">{{ bodyExtraKey }}</span>
        <code class="wf-node__extra-val">{{ bodyExtra }}</code>
      </div>
      <div class="wf-node__result" v-if="data.result">
        <svg width="10" height="10" viewBox="0 0 16 16" fill="none"><path d="M3 8l4 4 6-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        {{ data.result }}
      </div>
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

const NODE_META: Record<string, { label: string; icon: string; color: string; gradient: string }> = {
  'ontology-query': {
    label: '本体查询', color: '#3b82f6',
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  },
  'datasource': {
    label: '数据源连接', color: '#8b5cf6',
    gradient: 'linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>`,
  },
  'rule-engine': {
    label: '规则引擎', color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="13" cy="10" r="2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  },
  'llm-inference': {
    label: '大模型推理', color: '#10b981',
    gradient: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  },
  'ml-model': {
    label: '预测模型', color: '#06b6d4',
    gradient: 'linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 7l3 3 2-4 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  'write-back': {
    label: '结果写回', color: '#64748b',
    gradient: 'linear-gradient(135deg, #475569 0%, #64748b 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v8M5 8l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 13h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  },
  'notification': {
    label: '通知触达', color: '#ec4899',
    gradient: 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2a5 5 0 015 5v2l1 2H2l1-2V7a5 5 0 015-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6.5 13a1.5 1.5 0 003 0" stroke="currentColor" stroke-width="1.5"/></svg>`,
  },
  'human-approval': {
    label: '人工审批', color: '#f97316',
    gradient: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M11 9l1.5 1.5L15 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  'condition': {
    label: '条件判断', color: '#a855f7',
    gradient: 'linear-gradient(135deg, #a855f7 0%, #c084fc 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  },
  'loop': {
    label: '遍历列表', color: '#0ea5e9',
    gradient: 'linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 8a5 5 0 019.9-1M13 8a5 5 0 01-9.9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M12 4l1 3-3 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  'merge': {
    label: '合并分支', color: '#84cc16',
    gradient: 'linear-gradient(135deg, #84cc16 0%, #a3e635 100%)',
    icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 3v4l4 3 4-3V3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
}

const meta = computed(() => NODE_META[nodeType.value] || NODE_META['ontology-query'])
const nodeLabel = computed(() => meta.value.label)
const nodeIcon = computed(() => meta.value.icon)
const nodeGradient = computed(() => meta.value.gradient)
const execState = computed(() => props.data.execState || 'idle')

const stateLabel = computed(() => ({ idle: '待执行', running: '执行中', done: '完成', error: '错误' }[execState.value] || '待执行'))

const bodyExtra = computed(() => {
  if (nodeType.value === 'ontology-query') return props.data.ontology_type || ''
  if (nodeType.value === 'datasource') return props.data.sql ? props.data.sql.slice(0, 40) + '…' : ''
  if (nodeType.value === 'rule-engine') return props.data.rule_expr || ''
  if (nodeType.value === 'ml-model') return props.data.model_name || ''
  if (nodeType.value === 'notification') return props.data.notify_type || ''
  return ''
})

const bodyExtraKey = computed(() => {
  if (nodeType.value === 'ontology-query') return '对象'
  if (nodeType.value === 'datasource') return 'SQL'
  if (nodeType.value === 'rule-engine') return '条件'
  if (nodeType.value === 'ml-model') return '模型'
  if (nodeType.value === 'notification') return '方式'
  return ''
})

const stateClass = computed(() => {
  const s: string[] = []
  if (props.selected) s.push('wf-node--selected')
  if (execState.value === 'running') s.push('wf-node--running')
  if (execState.value === 'done') s.push('wf-node--done')
  if (execState.value === 'error') s.push('wf-node--error')
  return s
})
</script>

<style scoped>
.wf-node {
  width: 220px;
  height: 100px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  overflow: hidden;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
  cursor: pointer;
  display: flex;
  flex-direction: column;
}
.wf-node:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.10), 0 2px 6px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}
.wf-node--selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15), 0 8px 24px rgba(0,0,0,0.10);
}
.wf-node--running {
  border-color: #f59e0b;
  animation: wf-pulse 1.2s ease-in-out infinite;
}
.wf-node--done { border-color: #10b981; }
.wf-node--error { border-color: #ef4444; }

@keyframes wf-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245,158,11,.3); }
  50% { box-shadow: 0 0 0 6px rgba(245,158,11,0); }
}

.wf-node__topbar {
  height: 3px;
  width: 100%;
}

.wf-node__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px 8px;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}

.wf-node__icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.wf-node__icon {
  width: 14px;
  height: 14px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.wf-node__header-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.wf-node__type-label {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  line-height: 1;
}
.wf-node__name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.wf-node__state-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  border-radius: 20px;
  background: #f1f5f9;
  flex-shrink: 0;
}
.wf-node__state-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #94a3b8;
}
.wf-node__state-badge--running .wf-node__state-dot { background: #f59e0b; }
.wf-node__state-badge--done .wf-node__state-dot { background: #10b981; }
.wf-node__state-badge--error .wf-node__state-dot { background: #ef4444; }
.wf-node__state-badge--running { background: #fffbeb; }
.wf-node__state-badge--done { background: #f0fdf4; }
.wf-node__state-badge--error { background: #fef2f2; }
.wf-node__state-text {
  font-size: 10px;
  font-weight: 500;
  color: #64748b;
}
.wf-node__state-badge--running .wf-node__state-text { color: #d97706; }
.wf-node__state-badge--done .wf-node__state-text { color: #059669; }
.wf-node__state-badge--error .wf-node__state-text { color: #dc2626; }

.wf-node__body {
  padding: 6px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}
.wf-node__desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wf-node__extra {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  border-radius: 6px;
  padding: 4px 8px;
}
.wf-node__extra-key {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 600;
  flex-shrink: 0;
}
.wf-node__extra-val {
  font-size: 11px;
  color: #475569;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wf-node__result {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #059669;
  background: #f0fdf4;
  border-radius: 6px;
  padding: 4px 8px;
}

.wf-handle {
  width: 10px;
  height: 10px;
  background: #fff;
  border: 2px solid #cbd5e1;
  border-radius: 50%;
  transition: border-color 0.15s, transform 0.15s;
}
.wf-handle:hover {
  border-color: #3b82f6;
  transform: scale(1.3);
}
.wf-handle--in { left: -6px; }
.wf-handle--out { right: -6px; }
.wf-handle--bottom { bottom: -6px; right: 50%; transform: translateX(50%); }
</style>
