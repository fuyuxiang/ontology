<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { workflowApi } from '../../../api/workflow'
import type { ToolSpec } from '../../../types/workflow'

const tools = ref<ToolSpec[]>([])
const search = ref('')

onMounted(async () => {
  try { tools.value = await workflowApi.listTools() } catch { /* ignore */ }
})

const filtered = () => {
  const q = search.value.toLowerCase()
  return q ? tools.value.filter(t => t.name.toLowerCase().includes(q) || t.description.includes(q)) : tools.value
}
</script>
<template>
  <div class="panel">
    <input v-model="search" class="panel__search" placeholder="搜索工具..." />
    <div class="panel__list">
      <div v-for="t in filtered()" :key="t.name" class="panel__item">
        <div class="panel__item-head">
          <span class="panel__item-name">{{ t.name }}</span>
          <span v-if="t.sensitive" class="panel__badge">敏感</span>
        </div>
        <p class="panel__item-desc">{{ t.description }}</p>
        <div v-if="t.required.length" class="panel__item-params">
          参数: {{ t.required.join(', ') }}
        </div>
      </div>
      <p v-if="filtered().length === 0" class="panel__empty">无匹配工具</p>
    </div>
  </div>
</template>
<style scoped>
.panel { display: flex; flex-direction: column; gap: 8px; }
.panel__search { padding: 6px 10px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 12px; }
.panel__search:focus { border-color: var(--color-primary); outline: none; }
.panel__list { display: flex; flex-direction: column; gap: 6px; max-height: 400px; overflow-y: auto; }
.panel__item { padding: 8px; border: 1px solid var(--neutral-200); border-radius: 6px; }
.panel__item-head { display: flex; align-items: center; gap: 6px; }
.panel__item-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.panel__badge { font-size: 10px; padding: 1px 5px; border-radius: 4px; background: #fef3c7; color: #92400e; }
.panel__item-desc { font-size: 11px; color: var(--text-muted); margin: 2px 0 0; line-height: 1.4; }
.panel__item-params { font-size: 10px; color: var(--text-muted); margin-top: 4px; }
.panel__empty { font-size: 12px; color: var(--text-muted); text-align: center; padding: 20px; }
</style>
