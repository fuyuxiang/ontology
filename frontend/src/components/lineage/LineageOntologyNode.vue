<template>
  <div class="ln-node ln-node--ontology" :title="data.objectName">
    <Handle type="target" :position="Position.Left" class="ln-node__handle" />
    <div class="ln-node__main">@{{ data.label }}</div>
    <div v-if="data.tier" class="ln-node__tier">Tier {{ data.tier }}</div>
    <Handle type="source" :position="Position.Right" class="ln-node__handle" />
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: { label: string; objectName: string; tier?: number } }>()
</script>

<style scoped>
.ln-node--ontology {
  width: 120px;
  min-height: 44px;
  background: #F5F3FF;
  border: 2px solid #8B5CF6;
  border-radius: 10px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 700;
  color: #5b21b6;
  text-align: center;
  line-height: 1.2;
  box-sizing: border-box;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.ln-node--ontology:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.25);
}
.ln-node__main { line-height: 1.2; }
.ln-node__tier {
  font-size: 9px;
  color: #7c3aed;
  margin-top: 2px;
  font-weight: 600;
}
.ln-node__handle {
  background: #8B5CF6;
  width: 7px;
  height: 7px;
  border: none;
}
</style>
