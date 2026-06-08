<template>
  <div class="builder-page">
    <div class="builder-page__toolbar">
      <span class="builder-page__toolbar-label">工具选择</span>
      <select class="builder-page__select" v-model="editorMode">
        <option value="local">本地构建</option>
        <option value="protege">Protégé</option>
        <option value="webowl">WebOWL</option>
        <option value="vocbench">VocBench</option>
      </select>
    </div>

    <template v-if="editorMode === 'local'">
      <BuilderShell
        v-if="session"
        :session="session"
        @back="onBack"
        @goto-studio="gotoStudio"
      />
      <div v-else class="builder-page__loading">正在初始化构建会话…</div>
    </template>

    <ProtegeEditor v-else-if="editorMode === 'protege'" />
    <WebVowlEditor v-else-if="editorMode === 'webowl'" />
    <VocBenchEditor v-else />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBuilderStore } from '../../store/builder'
import ProtegeEditor from './components/protege/ProtegeEditor.vue'
import WebVowlEditor from './components/WebVowlEditor.vue'
import VocBenchEditor from './components/VocBenchEditor.vue'
import BuilderShell from './components/BuilderShell.vue'

const router = useRouter()
const store = useBuilderStore()
const { sessions, activeSession } = storeToRefs(store)

const editorMode = ref<'local' | 'protege' | 'webowl' | 'vocbench'>('local')

const session = computed(() => {
  if (activeSession.value && activeSession.value.buildMethod === 'manual') return activeSession.value
  return sessions.value.find(s => s.buildMethod === 'manual' && s.status !== 'published') || null
})

function ensureSession() {
  if (editorMode.value === 'local' && !session.value) {
    store.createSession({
      ontologyName: `本地构建-${Date.now().toString(36).slice(-4)}`,
      buildMethod: 'manual',
    })
  }
}

function onBack() {
  editorMode.value = 'protege'
}

function gotoStudio() {
  router.push('/studio')
}

watch(editorMode, (mode) => {
  if (mode === 'local') ensureSession()
})

onMounted(() => {
  if (editorMode.value === 'local') {
    if (session.value) {
      store.setActiveSession(session.value.sessionId)
    } else {
      ensureSession()
    }
  }
})
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
.builder-page__loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}
</style>
