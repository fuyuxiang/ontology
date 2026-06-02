<template>
  <div class="builder-page">
    <div class="builder-page__toolbar">
      <span class="builder-page__toolbar-label">工具选择</span>
      <select class="builder-page__select" v-model="editorMode">
        <option value="protege">Protégé</option>
        <option value="webowl">WebOWL</option>
        <option value="vocbench">VocBench</option>
      </select>
    </div>
    <ProtegeEditor v-if="editorMode === 'protege'" />
    <WebVowlEditor v-else-if="editorMode === 'webowl'" />
    <VocBenchEditor v-else />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ProtegeEditor from './components/protege/ProtegeEditor.vue'
import WebVowlEditor from './components/WebVowlEditor.vue'
import VocBenchEditor from './components/VocBenchEditor.vue'

const editorMode = ref<'protege' | 'webowl' | 'vocbench'>('protege')
</script>

<style scoped>
.builder-page { height: 100%; display: flex; flex-direction: column; }
.builder-page__toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: #f5f5f5;
  border-bottom: 1px solid #d8d8d8;
  flex-shrink: 0;
}
.builder-page__toolbar-label {
  font-size: 12px;
  color: #555;
}
.builder-page__select {
  font-size: 12px;
  padding: 3px 8px;
  border: 1px solid #c0c0c0;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
}
.builder-page__placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #666;
}
.builder-page__placeholder-icon { font-size: 48px; }
.builder-page__placeholder-title { font-size: 18px; font-weight: 600; color: #333; }
.builder-page__placeholder-sub { font-size: 13px; color: #999; }
</style>
