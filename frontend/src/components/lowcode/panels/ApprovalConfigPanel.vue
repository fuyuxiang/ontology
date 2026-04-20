<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { workflowApi } from '../../../api/workflow'
import type { ToolSpec } from '../../../types/workflow'

const props = defineProps<{ config: Record<string, any> }>()
const emit = defineEmits<{ (e: 'update', val: Record<string, any>): void }>()

const tools = ref<ToolSpec[]>([])

onMounted(async () => {
  try { tools.value = (await workflowApi.listTools()).filter(t => t.sensitive) } catch { /* ignore */ }
})

function toggleTool(name: string) {
  const current: string[] = props.config.sensitiveTools || []
  const next = current.includes(name) ? current.filter(t => t !== name) : [...current, name]
  emit('update', { ...props.config, sensitiveTools: next })
}
</script>
<template>
  <div class="panel">
    <div class="panel__field">
      <span>需要审批的敏感工具</span>
      <div class="panel__tools">
        <label v-for="t in tools" :key="t.name" class="panel__tool">
          <input type="checkbox" :checked="(config.sensitiveTools || []).includes(t.name)" @change="toggleTool(t.name)" />
          <span>{{ t.name }}</span>
        </label>
        <p v-if="tools.length === 0" class="panel__hint">暂无标记为敏感的工具</p>
      </div>
    </div>
  </div>
</template>
<style scoped>
.panel { display: flex; flex-direction: column; gap: 2px; }
.panel__field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; font-size: 12px; }
.panel__field > span { font-weight: 600; color: var(--text-secondary); }
.panel__tools { display: flex; flex-direction: column; gap: 4px; }
.panel__tool { display: flex; align-items: center; gap: 6px; font-size: 12px; padding: 4px 6px; border-radius: 4px; cursor: pointer; }
.panel__tool:hover { background: var(--bg-hover); }
.panel__hint { font-size: 11px; color: var(--text-muted); }
</style>
