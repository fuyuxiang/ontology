<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { workflowApi } from '../../../api/workflow'
import type { ToolSpec } from '../../../types/workflow'

const props = defineProps<{ config: Record<string, any> }>()
const emit = defineEmits<{ (e: 'update', val: Record<string, any>): void }>()

const tools = ref<ToolSpec[]>([])

onMounted(async () => {
  try { tools.value = await workflowApi.listTools() } catch { /* ignore */ }
})

function update(key: string, val: any) {
  emit('update', { ...props.config, [key]: val })
}

function toggleTool(name: string) {
  const current: string[] = props.config.boundTools || []
  const next = current.includes(name) ? current.filter(t => t !== name) : [...current, name]
  update('boundTools', next)
}
</script>
<template>
  <div class="panel">
    <label class="panel__field"><span>角色设定 (Persona)</span>
      <textarea :value="config.persona || ''" @input="update('persona', ($event.target as HTMLTextAreaElement).value)" class="panel__textarea" rows="3" placeholder="定义 Agent 的角色和行为..."></textarea>
    </label>
    <label class="panel__field"><span>目标 (Objective)</span>
      <textarea :value="config.objective || ''" @input="update('objective', ($event.target as HTMLTextAreaElement).value)" class="panel__textarea" rows="2" placeholder="Agent 的工作目标..."></textarea>
    </label>
    <label class="panel__field"><span>最大推理轮次</span>
      <input type="number" :value="config.maxSteps || 8" @input="update('maxSteps', +($event.target as HTMLInputElement).value)" class="panel__input" min="1" max="20" />
    </label>
    <div class="panel__field">
      <span>绑定工具 ({{ (config.boundTools || []).length }}/{{ tools.length }})</span>
      <div class="panel__tools">
        <label v-for="t in tools" :key="t.name" class="panel__tool" :class="{ 'panel__tool--sensitive': t.sensitive }">
          <input type="checkbox" :checked="(config.boundTools || []).includes(t.name)" @change="toggleTool(t.name)" />
          <span>{{ t.name }}</span>
          <span v-if="t.sensitive" class="panel__badge panel__badge--warn">敏感</span>
        </label>
      </div>
    </div>
  </div>
</template>
<style scoped>
.panel { display: flex; flex-direction: column; gap: 2px; }
.panel__field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; font-size: 12px; }
.panel__field > span { font-weight: 600; color: var(--text-secondary); }
.panel__input { padding: 6px 10px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 13px; }
.panel__input:focus { border-color: var(--color-primary); outline: none; }
.panel__textarea { padding: 8px 10px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 13px; resize: vertical; font-family: inherit; line-height: 1.5; }
.panel__textarea:focus { border-color: var(--color-primary); outline: none; }
.panel__tools { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; }
.panel__tool { display: flex; align-items: center; gap: 6px; font-size: 12px; padding: 4px 6px; border-radius: 4px; cursor: pointer; }
.panel__tool:hover { background: var(--bg-hover); }
.panel__tool--sensitive { color: #dc2626; }
.panel__badge { font-size: 10px; padding: 1px 5px; border-radius: 4px; }
.panel__badge--warn { background: #fef3c7; color: #92400e; }
</style>
