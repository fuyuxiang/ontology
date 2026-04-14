<template>
  <div class="canvas-toolbar">
    <div class="canvas-toolbar__left">
      <button class="toolbar-btn" title="自动布局" @click="$emit('layout')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="10" y="1" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="5.5" y="10" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M3.5 6v2.5a1 1 0 001 1h3m5-3.5v2.5a1 1 0 01-1 1h-3" stroke="currentColor" stroke-width="1.5"/></svg>
        布局
      </button>
      <div class="toolbar-sep"></div>
      <button class="toolbar-btn" title="适应画布" @click="$emit('fit')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M1 5V2a1 1 0 011-1h3m6 0h3a1 1 0 011 1v3m0 6v3a1 1 0 01-1 1h-3m-6 0H2a1 1 0 01-1-1v-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        适应
      </button>
      <div class="toolbar-sep"></div>
      <button class="toolbar-btn" :class="{ 'toolbar-btn--active': direction === 'LR' }" @click="$emit('direction', 'LR')">水平</button>
      <button class="toolbar-btn" :class="{ 'toolbar-btn--active': direction === 'TB' }" @click="$emit('direction', 'TB')">垂直</button>
    </div>
    <div class="canvas-toolbar__right">
      <span class="toolbar-stats text-caption">{{ nodeCount }} 对象 · {{ edgeCount }} 关系</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ direction: 'LR' | 'TB'; nodeCount: number; edgeCount: number }>()
defineEmits<{ layout: []; fit: []; direction: [d: 'LR' | 'TB'] }>()
</script>

<style scoped>
.canvas-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  height: 44px; padding: 0 16px;
  background: #fff; border-bottom: 1px solid #e9ecef;
  flex-shrink: 0;
}
.canvas-toolbar__left { display: flex; align-items: center; gap: 4px; }
.toolbar-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 10px; border: 1px solid #e9ecef; border-radius: 6px;
  background: #f8f9fa; color: #495057; font-size: 12px; font-weight: 500;
  cursor: pointer; transition: all 0.15s;
}
.toolbar-btn:hover { background: #e9ecef; }
.toolbar-btn--active { background: #4c6ef5; color: #fff; border-color: #4c6ef5; }
.toolbar-sep { width: 1px; height: 20px; background: #e9ecef; margin: 0 4px; }
.toolbar-stats { color: #868e96; }
</style>
