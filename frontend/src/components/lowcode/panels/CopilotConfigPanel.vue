<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ config: Record<string, any>; agentNodes: { id: string; label: string }[] }>()
const emit = defineEmits<{ (e: 'update', val: Record<string, any>): void }>()

function update(key: string, val: any) {
  emit('update', { ...props.config, [key]: val })
}
</script>
<template>
  <div class="panel">
    <label class="panel__field"><span>标题</span>
      <input :value="config.title || ''" @input="update('title', ($event.target as HTMLInputElement).value)" class="panel__input" placeholder="Copilot Chat" />
    </label>
    <label class="panel__field"><span>绑定 Agent 节点</span>
      <select :value="config.boundAgentNodeId || ''" @change="update('boundAgentNodeId', ($event.target as HTMLSelectElement).value)" class="panel__input">
        <option value="">-- 选择 Agent --</option>
        <option v-for="a in agentNodes" :key="a.id" :value="a.id">{{ a.label }}</option>
      </select>
    </label>
    <label class="panel__field"><span>欢迎语</span>
      <textarea :value="config.welcomeMessage || ''" @input="update('welcomeMessage', ($event.target as HTMLTextAreaElement).value)" class="panel__textarea" rows="2" placeholder="你好，有什么可以帮你？"></textarea>
    </label>
  </div>
</template>
<style scoped>
.panel { display: flex; flex-direction: column; gap: 2px; }
.panel__field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; font-size: 12px; }
.panel__field > span { font-weight: 600; color: var(--text-secondary); }
.panel__input { padding: 6px 10px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 13px; }
.panel__input:focus { border-color: var(--color-primary); outline: none; }
.panel__textarea { padding: 8px 10px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 13px; resize: vertical; font-family: inherit; }
.panel__textarea:focus { border-color: var(--color-primary); outline: none; }
</style>
