<template>
  <div class="glass-panel control-bar">
    <button v-for="l in layouts" :key="l.id" class="ctrl-btn" :class="{ 'ctrl-btn--active': active === l.id }" @click="setLayout(l.id)" :title="l.tip">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path :d="l.icon" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
    <span class="ctrl-sep"></span>
    <button class="ctrl-btn" @click="$emit('zoom-in')" title="放大">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 3v8M3 7h8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
    </button>
    <button class="ctrl-btn" @click="$emit('zoom-out')" title="缩小">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
    </button>
    <button class="ctrl-btn" @click="$emit('fit')" title="适配视图">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="2" y="2" width="10" height="10" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M5 7h4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  layout: [type: string]
  'zoom-in': []
  'zoom-out': []
  fit: []
}>()

const active = ref('force')

const layouts = [
  { id: 'force', tip: 'Force 力导向', icon: 'M3 7a4 4 0 108 0 4 4 0 00-8 0zM7 3v1M7 10v1M3 7h1M10 7h1' },
  { id: 'dagre', tip: 'Dagre 层级', icon: 'M7 2v4M4 6h6M4 6v3M10 6v3M4 9h2M8 9h2M2 12h4M8 12h4' },
  { id: 'radial', tip: 'Radial 径向', icon: 'M7 7m-2 0a2 2 0 104 0 2 2 0 00-4 0M7 7m-5 0a5 5 0 1010 0 5 5 0 00-10 0' },
]

function setLayout(id: string) {
  active.value = id
  emit('layout', id)
}
</script>

<style scoped>
.glass-panel {
  position: absolute;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  color: var(--neutral-300);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 14px;
  pointer-events: auto;
  z-index: 10;
}
.control-bar {
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
}
.ctrl-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--neutral-500);
  cursor: pointer;
  transition: background .15s, color .15s;
}
.ctrl-btn:hover { background: rgba(148,163,184,.12); color: var(--neutral-300); }
.ctrl-btn--active { background: rgba(16,185,129,.15); color: var(--status-success); }
.ctrl-sep { width: 1px; height: 18px; background: rgba(148,163,184,.15); margin: 0 4px; }
</style>
