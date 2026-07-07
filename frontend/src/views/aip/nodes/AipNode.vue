<template>
  <div class="aip-node" :class="[`aip-node--${cardType}`, `aip-status-${statusClass}`, { 'aip-node--selected': selected }]">
    <!-- 状态徽章 -->
    <div v-if="statusClass !== 'idle'" class="aip-node-status-badge" :style="{ background: statusColor }">
      <span v-if="statusClass === 'running'" class="aip-spin">⟳</span>
      <span v-else-if="statusClass === 'success'">✓</span>
      <span v-else-if="statusClass === 'error'">✕</span>
      <span v-else>⏱</span>
    </div>

    <!-- 顶部入口 Handle（每个节点都有） -->
    <Handle v-if="!isSubNode" type="target" :position="Position.Left" id="target-0" :style="{ background: '#555' }" />

    <!-- 卡片 -->
    <div class="aip-node-card" :style="{ borderColor: selected ? color : '#d9d9d9', boxShadow: selected ? `0 0 0 2px ${color}33` : '0 1px 2px 0 rgba(0,0,0,0.05)' }">
      <div class="aip-node-card__header" :style="{ background: color + '0a', borderBottomColor: '#e6e6e6' }">
        <div class="aip-node-card__icon" :style="{ background: color }" v-html="iconSvg"></div>
        <span class="aip-node-card__title">{{ data.label || '未命名节点' }}</span>
        <span class="aip-node-card__tag" :style="{ background: color + '10', color, borderColor: color + '40' }">{{ tagLabel }}</span>
      </div>
      <div class="aip-node-card__body">
        <!-- ontologyQuery -->
        <template v-if="type === 'ontologyQuery'">
          <div class="aip-field">
            <span class="aip-field__label">关联本体</span>
            <div class="aip-tag-row">
              <span v-for="t in (data.objectTypes || (data.objectType ? [data.objectType] : []))" :key="t" class="aip-tag aip-tag--blue">{{ t }}</span>
              <span v-if="!(data.objectTypes && data.objectTypes.length) && !data.objectType" class="aip-field__empty">未选择</span>
            </div>
          </div>
          <div v-if="data.filters && data.filters.length" class="aip-field">
            <span class="aip-field__label">过滤条件 ({{ data.filters.length }})</span>
          </div>
        </template>

        <!-- llmAgent -->
        <template v-else-if="type === 'llmAgent'">
          <div class="aip-field"><span class="aip-field__label">LLM 模型</span><span class="aip-field__value">{{ data.model || '未配置' }}</span></div>
          <div class="aip-field"><span class="aip-field__label">ML 模型</span><span class="aip-field__value">{{ mlLabel(data.mlModelRef) }}</span></div>
          <div class="aip-field"><span class="aip-field__label">温度</span><span class="aip-field__value">{{ data.temperature ?? 0.3 }}</span></div>
        </template>

        <!-- agentNode -->
        <template v-else-if="type === 'agentNode'">
          <div class="aip-field"><span class="aip-field__label">主 Skill</span><span class="aip-field__value">{{ data.primarySkillId || '—' }}</span></div>
          <div class="aip-field"><span class="aip-field__label">关联本体</span>
            <div class="aip-tag-row">
              <span v-for="t in (data.objectTypes || []).slice(0, 3)" :key="t" class="aip-tag aip-tag--green">{{ t }}</span>
              <span v-if="(data.objectTypes || []).length > 3" class="aip-tag aip-tag--gray">+{{ data.objectTypes.length - 3 }}</span>
            </div>
          </div>
        </template>

        <!-- skillNode -->
        <template v-else-if="type === 'skillNode'">
          <div class="aip-field">
            <span v-for="(s, i) in (data.skills || [])" :key="i" class="aip-line">
              <span class="aip-dot aip-dot--green"></span>{{ s.name || s.skillId }}<span v-if="s.isPrimary" class="aip-tag aip-tag--gold aip-tag--sm">主</span>
            </span>
            <span v-if="!(data.skills || []).length" class="aip-field__empty">无 Skill</span>
          </div>
        </template>

        <!-- memoryNode -->
        <template v-else-if="type === 'memoryNode'">
          <div class="aip-field">
            <span v-for="(m, i) in (data.memories || [])" :key="i" class="aip-line"><span class="aip-dot aip-dot--purple"></span>{{ m.layer || '—' }}：{{ m.impl || '—' }}</span>
            <span v-if="!(data.memories || []).length" class="aip-field__empty">未配置</span>
          </div>
        </template>

        <!-- toolNode -->
        <template v-else-if="type === 'toolNode'">
          <div class="aip-field">
            <span v-for="(t, i) in (data.tools || [])" :key="i" class="aip-line"><span class="aip-dot aip-dot--cyan"></span>{{ t.name || t.toolId }}</span>
            <span v-if="!(data.tools || []).length" class="aip-field__empty">无 Tool</span>
          </div>
        </template>

        <!-- writebackOntology -->
        <template v-else-if="type === 'writebackOntology'">
          <div class="aip-field"><span class="aip-field__label">写回对象</span><span class="aip-field__value">{{ data.targetObjectType || '—' }}</span></div>
          <div class="aip-field"><span class="aip-field__label">操作</span><span class="aip-field__value">{{ data.operation || 'create' }}</span></div>
        </template>

        <!-- actionSystem -->
        <template v-else-if="type === 'actionSystem'">
          <div class="aip-field"><span class="aip-field__label">目标对象</span><span class="aip-field__value">{{ data.targetObjectType || data.writebackTarget || '—' }}</span></div>
          <div class="aip-field"><span class="aip-field__label">API</span><span class="aip-field__value">{{ data.apiName || '—' }}</span></div>
        </template>

        <!-- condition -->
        <template v-else-if="type === 'condition'">
          <div class="aip-field"><span class="aip-field__label">条件字段</span><span class="aip-field__value">{{ data.expression?.field || data.conditionField || '—' }}</span></div>
          <div v-if="data.branches && data.branches.length" class="aip-field"><span class="aip-field__label">分支 ({{ data.branches.length }})</span></div>
        </template>
      </div>
    </div>

    <!-- 出口 Handle —— 普通节点 -->
    <Handle v-if="!isAgent && !isSubNode" type="source" :position="Position.Right" id="source-0" :style="{ background: '#555' }" />

    <!-- 出口 Handle —— Agent 4 个 sub handle -->
    <template v-if="isAgent">
      <Handle type="source" :position="Position.Right" id="source-0" :style="{ background: '#555', top: '50%' }" />
      <Handle type="source" :position="Position.Bottom" id="sub-skill" :style="{ background: '#10b981', left: '20%' }" />
      <Handle type="source" :position="Position.Bottom" id="sub-memory" :style="{ background: '#7c3aed', left: '40%' }" />
      <Handle type="source" :position="Position.Bottom" id="sub-tool" :style="{ background: '#0ea5e9', left: '60%' }" />
      <Handle type="source" :position="Position.Bottom" id="sub-llm" :style="{ background: '#f59e0b', left: '80%' }" />
    </template>

    <!-- 子节点入口 Handle -->
    <Handle v-if="isSubNode" type="target" :position="Position.Top" id="target-top" :style="{ background: subColor }" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { ML_MODELS, NODE_TYPES } from '../aipData'

const props = defineProps<{
  id: string
  type: string
  data: Record<string, any>
  selected: boolean
  status?: string
}>()

const meta = computed(() => NODE_TYPES.find(t => t.type === props.type))
const color = computed(() => meta.value?.color || '#94a3b8')
const tagLabel = computed(() => meta.value?.label || props.type)
const isAgent = computed(() => props.type === 'agentNode')
const isSubNode = computed(() => ['skillNode', 'memoryNode', 'toolNode', 'llmAgent'].includes(props.type))
const subColor = computed(() => ({
  skillNode: '#10b981',
  memoryNode: '#7c3aed',
  toolNode: '#0ea5e9',
  llmAgent: '#f59e0b',
}[props.type] || '#555'))
const cardType = computed(() => isSubNode.value ? 'sub' : 'main')
const statusClass = computed(() => props.status || 'idle')
const statusColor = computed(() => ({
  running: '#3b82f6', success: '#10b981', error: '#ef4444', waiting: '#f59e0b', idle: 'transparent',
}[statusClass.value]))

function mlLabel(value?: string) {
  return ML_MODELS.find(m => m.value === value)?.label || value || '未配置'
}

const iconSvg = computed(() => {
  const m: Record<string, string> = {
    ontologyQuery: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="#fff" stroke-width="1.5"/><path d="M3 4v8c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="#fff" stroke-width="1.5"/></svg>',
    llmAgent: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>',
    agentNode: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="#fff" stroke-width="1.5"/><path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>',
    skillNode: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M9 1L3 9h4l-1 6 6-8H8l1-6z" fill="#fff"/></svg>',
    memoryNode: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="2" stroke="#fff" stroke-width="1.5"/><path d="M5 6h6M5 9h6" stroke="#fff" stroke-width="1.2"/></svg>',
    toolNode: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M10 2a3 3 0 00-2.83 4L3 10.17V13h2.83L10 8.83A3 3 0 1010 2z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>',
    ruleEngine: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 3h10M3 8h7M3 13h10" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>',
    writebackOntology: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 2h7l3 3v9H3V2z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 2v4h4V2" stroke="#fff" stroke-width="1.5"/></svg>',
    actionSystem: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8l11-5-3 12-3-5-5-2z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>',
    condition: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  }
  return m[props.type] || '<svg width="14" height="14"></svg>'
})
</script>

<style scoped>
.aip-node { position: relative; }
.aip-node-card {
  border: 1.5px solid #d9d9d9;
  border-radius: 8px;
  background: #fff;
  min-width: 220px;
  max-width: 280px;
  font-size: 12px;
  transition: box-shadow .2s, border-color .2s;
}
.aip-node--sub .aip-node-card { min-width: 180px; max-width: 240px; }
.aip-node-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid #e6e6e6;
  border-radius: 8px 8px 0 0;
}
.aip-node-card__icon {
  width: 22px; height: 22px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.aip-node-card__title { font-weight: 600; font-size: 13px; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.aip-node-card__tag { font-size: 10px; padding: 1px 6px; border-radius: 4px; border: 1px solid; flex-shrink: 0; }
.aip-node-card__body { padding: 10px 12px; display: flex; flex-direction: column; gap: 6px; }

.aip-field { font-size: 11px; }
.aip-field__label { display: block; color: #94a3b8; font-size: 10px; margin-bottom: 3px; }
.aip-field__value { color: #475569; font-weight: 500; }
.aip-field__empty { color: #cbd5e1; font-size: 10px; }
.aip-tag-row { display: flex; flex-wrap: wrap; gap: 4px; }
.aip-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; border: 1px solid transparent; }
.aip-tag--blue { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.aip-tag--green { background: #ecfdf5; color: #059669; border-color: #a7f3d0; }
.aip-tag--orange { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
.aip-tag--gold { background: #fef3c7; color: #b45309; border-color: #fde68a; }
.aip-tag--gray { background: #f1f5f9; color: #64748b; }
.aip-tag--sm { padding: 0 4px; font-size: 9px; }
.aip-line { display: flex; align-items: center; gap: 6px; line-height: 18px; color: #475569; }
.aip-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.aip-dot--green { background: #10b981; }
.aip-dot--purple { background: #7c3aed; }
.aip-dot--cyan { background: #0ea5e9; }

.aip-node-status-badge {
  z-index: 10;
  color: #fff;
  border: 2px solid #fff;
  border-radius: 50%;
  width: 20px; height: 20px;
  font-size: 11px;
  display: flex; justify-content: center; align-items: center;
  position: absolute; top: -6px; right: -6px;
}
.aip-spin { animation: aip-spin 1s linear infinite; display: inline-block; }
@keyframes aip-spin { to { transform: rotate(360deg); } }

.aip-status-running .aip-node-card { border-color: #3b82f6 !important; animation: aip-node-pulse 1.5s ease-in-out infinite; box-shadow: 0 0 0 3px rgba(59,130,246,.15) !important; }
.aip-status-success .aip-node-card { border-color: #10b981 !important; box-shadow: 0 0 0 2px rgba(16,185,129,.12) !important; }
.aip-status-error .aip-node-card { border-color: #ef4444 !important; box-shadow: 0 0 0 2px rgba(239,68,68,.15) !important; }
.aip-status-waiting .aip-node-card { border-color: #f59e0b !important; box-shadow: 0 0 0 2px rgba(245,158,11,.15) !important; }
@keyframes aip-node-pulse { 0% { box-shadow: 0 0 0 0 rgba(59,130,246,.35) } 50% { box-shadow: 0 0 0 6px rgba(59,130,246,0) } 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0) } }
</style>
