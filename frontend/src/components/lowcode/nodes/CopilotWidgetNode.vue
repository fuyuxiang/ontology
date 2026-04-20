<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: any; id: string; selected?: boolean }>()
</script>
<template>
  <div class="lc-node lc-node--ui" :class="{ 'lc-node--selected': selected }">
    <div class="lc-node__header lc-node__header--blue">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V4z" stroke="#fff" stroke-width="1.5"/><path d="M5 7h6M5 10h3" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>{{ data.label || 'Copilot Chat' }}</span>
    </div>
    <div class="lc-node__body">
      <div class="lc-node__preview">
        <div class="lc-node__chat-bubble">你好，有什么可以帮你？</div>
        <div class="lc-node__chat-input">输入消息...</div>
      </div>
    </div>
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />
  </div>
</template>
<style scoped>
.lc-node { border-radius: 10px; border: 2px solid var(--neutral-200); background: var(--bg-primary); min-width: 180px; font-size: 12px; }
.lc-node--selected { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
.lc-node--ui { border-color: #93c5fd; }
.lc-node__header { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 8px 8px 0 0; color: #fff; font-weight: 600; font-size: 12px; }
.lc-node__header--blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.lc-node__body { padding: 8px 10px; }
.lc-node__preview { display: flex; flex-direction: column; gap: 4px; }
.lc-node__chat-bubble { background: var(--neutral-100); padding: 4px 8px; border-radius: 8px; font-size: 11px; color: var(--text-secondary); }
.lc-node__chat-input { border: 1px solid var(--neutral-200); padding: 3px 8px; border-radius: 6px; font-size: 10px; color: var(--text-muted); }
</style>
