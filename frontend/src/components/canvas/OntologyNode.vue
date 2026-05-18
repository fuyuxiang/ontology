<template>
  <div
    class="ont-node"
    :class="[`ont-node--t${data.tier}`, { 'ont-node--selected': selected, 'ont-node--dimmed': data._dimmed }]"
    @mouseenter="showTooltip = true"
    @mouseleave="showTooltip = false"
  >
    <Handle type="target" :position="Position.Left" class="ont-node__handle" />
    <div class="ont-node__circle">
      <span class="ont-node__label">{{ data.nameCn }}</span>
    </div>
    <div class="ont-node__sub">{{ data.name }}</div>
    <Handle type="source" :position="Position.Right" class="ont-node__handle" />

    <!-- Hover tooltip -->
    <Transition name="tooltip-fade">
      <div v-if="showTooltip" class="ont-node__tooltip">
        <div class="tooltip__header">
          <span class="tooltip__tier">T{{ data.tier }} · {{ tierLabel }}</span>
          <span class="tooltip__status" :class="`tooltip__status--${data.status}`"></span>
        </div>
        <div class="tooltip__name">{{ data.nameCn }}</div>
        <div class="tooltip__en">{{ data.name }}</div>
        <div class="tooltip__stats">
          <span v-if="data.attrCount"><strong>{{ data.attrCount }}</strong> 属性</span>
          <span v-if="data.relCount"><strong>{{ data.relCount }}</strong> 关系</span>
          <span v-if="data.actionCount"><strong>{{ data.actionCount }}</strong> 动作</span>
          <span v-if="data.ruleCount"><strong>{{ data.ruleCount }}</strong> 规则</span>
          <span v-if="data.functionCount"><strong>{{ data.functionCount }}</strong> 函数</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  data: { name: string; nameCn: string; tier: 1 | 2 | 3; status: string; relCount: number; attrCount?: number; actionCount?: number; ruleCount?: number; functionCount?: number; _dimmed?: boolean; _highlight?: boolean }
  selected?: boolean
  sourcePosition?: Position
  targetPosition?: Position
}>()

const showTooltip = ref(false)
const tierLabel = computed(() => ({ 1: '核心', 2: '领域', 3: '场景' }[props.data.tier]))
</script>

<style scoped>
.ont-node--t1 { --tc: #4f6ef7; --tc-light: rgba(79,110,247,0.12); --tc-glow: rgba(79,110,247,0.3); }
.ont-node--t2 { --tc: #a855f7; --tc-light: rgba(168,85,247,0.12); --tc-glow: rgba(168,85,247,0.3); }
.ont-node--t3 { --tc: #10b981; --tc-light: rgba(16,185,129,0.12); --tc-glow: rgba(16,185,129,0.3); }

.ont-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: opacity 0.25s ease;
}

.ont-node--dimmed { opacity: 0.2; pointer-events: none; }

.ont-node__circle {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: var(--tc-light);
  border: 2.5px solid var(--tc);
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1),
              box-shadow 0.2s ease,
              border-color 0.2s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.ont-node:hover .ont-node__circle {
  transform: scale(1.1);
  box-shadow: 0 4px 20px var(--tc-glow), 0 0 0 4px var(--tc-light);
}

.ont-node--selected .ont-node__circle {
  transform: scale(1.12);
  box-shadow: 0 4px 24px var(--tc-glow), 0 0 0 5px var(--tc-light);
  border-width: 3px;
}

.ont-node__label {
  font-size: 11px;
  font-weight: 700;
  color: var(--tc);
  text-align: center;
  line-height: 1.2;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.ont-node__sub {
  margin-top: 4px;
  font-size: 9px;
  color: #94a3b8;
  font-family: monospace;
  max-width: 80px;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ont-node__handle {
  width: 8px; height: 8px;
  background: var(--tc);
  border: 2px solid #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  opacity: 0;
  transition: opacity 0.15s;
}
.ont-node:hover .ont-node__handle { opacity: 1; }

/* Tooltip */
.ont-node__tooltip {
  position: absolute;
  top: -8px;
  left: calc(100% + 12px);
  z-index: 100;
  min-width: 160px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.1), 0 2px 6px rgba(0,0,0,0.04);
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tooltip__header {
  display: flex; align-items: center; justify-content: space-between;
}
.tooltip__tier {
  font-size: 10px; font-weight: 700; color: var(--tc);
  background: var(--tc-light);
  padding: 1px 7px; border-radius: 4px;
}
.tooltip__status { width: 7px; height: 7px; border-radius: 50%; }
.tooltip__status--active { background: #10b981; }
.tooltip__status--warning { background: #f59e0b; }
.tooltip__status--error { background: #ef4444; }

.tooltip__name { font-size: 13px; font-weight: 700; color: #1e293b; }
.tooltip__en { font-size: 10px; color: #94a3b8; font-family: monospace; }
.tooltip__stats {
  display: flex; gap: 10px; margin-top: 4px;
  padding-top: 4px; border-top: 1px solid #f1f5f9;
  font-size: 11px; color: #64748b;
}
.tooltip__stats strong { color: #1e293b; }

.tooltip-fade-enter-active { transition: opacity 0.15s, transform 0.15s; }
.tooltip-fade-leave-active { transition: opacity 0.1s; }
.tooltip-fade-enter-from { opacity: 0; transform: translateX(-4px); }
.tooltip-fade-leave-to { opacity: 0; }
</style>
