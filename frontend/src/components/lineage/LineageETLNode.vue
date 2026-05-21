<template>
  <div class="ln-node ln-node--etl" :title="data.label">
    <Handle type="target" :position="Position.Left" class="ln-node__handle" />
    <span class="ln-node__icon">⚙️</span>
    <span class="ln-node__label">{{ data.label }}</span>
    <Handle type="source" :position="Position.Right" class="ln-node__handle" />
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: { label: string } }>()
</script>

<style scoped>
.ln-node--etl {
  width: 132px;
  min-height: 34px;
  background: #ECFDF5;
  border: 1.5px dashed #10b981;
  border-radius: 6px;
  padding: 7px 12px;
  font-size: 11px;
  color: #065f46;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1.2;
  box-sizing: border-box;
}
.ln-node__icon { margin-right: 4px; font-size: 11px; flex: 0 0 auto; }
.ln-node__label { white-space: pre-line; }
.ln-node__handle {
  background: #10b981;
  width: 6px;
  height: 6px;
  border: none;
}
</style>
