<template>
  <div class="ln-node ln-node--source" :title="data.label">
    <Handle type="target" :position="Position.Left" class="ln-node__handle ln-node__handle--hidden" />
    <span class="ln-node__icon">🗄️</span>
    <span class="ln-node__label">{{ data.label }}</span>
    <Handle type="source" :position="Position.Right" class="ln-node__handle ln-node__handle--right" />
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: { label: string } }>()
</script>

<style scoped>
.ln-node--source {
  width: 156px;
  min-height: 36px;
  background: #EBF5FF;
  border: 2px solid #4a9eff;
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 600;
  color: #1a3db5;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1.25;
  box-sizing: border-box;
}
.ln-node__icon { margin-right: 5px; flex: 0 0 auto; }
.ln-node__label { white-space: pre-line; }
.ln-node__handle--hidden { visibility: hidden; }
.ln-node__handle--right {
  background: #4a9eff;
  width: 7px;
  height: 7px;
  border: none;
}
</style>
