<template>
  <div class="ai-builder">
    <div class="ai-builder__steps">
      <div v-for="(s, i) in steps" :key="i" class="ai-builder__step" :class="{ 'ai-builder__step--active': step === i, 'ai-builder__step--done': step > i }">
        <div class="ai-builder__step-num">{{ step > i ? '✓' : i + 1 }}</div>
        <div class="ai-builder__step-label">{{ s }}</div>
      </div>
    </div>

    <div class="ai-builder__content">
      <div v-if="!session" class="ai-builder__loading">正在初始化…</div>
      <Step1Import v-else-if="step === 0" :session="session" @next="onImportDone" />
      <div v-else-if="step === 1" class="ai-builder__review">
        <Step2Review :session="session!" @prev="step = 0" @next="step = 2" />
      </div>
      <div v-else-if="step === 2" class="ai-builder__hydrate">
        <Step3Hydrate :session="session!" @prev="step = 1" @goto-studio="gotoStudio" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBuilderStore } from '../../store/builder'
import Step1Import from './components/Step1Import.vue'
import Step2Review from './components/Step2Review.vue'
import Step3Hydrate from './components/Step3Hydrate.vue'

const router = useRouter()
const route = useRoute()
const store = useBuilderStore()
const { sessions, activeSession } = storeToRefs(store)

const steps = ['文件导入', '专家审核', '水合验证']
const step = ref(0)

const session = computed(() => {
  if (activeSession.value && activeSession.value.buildMethod === 'import') return activeSession.value
  return sessions.value.find(s => s.buildMethod === 'import' && s.status === 'drafting') || null
})

function onImportDone() {
  step.value = 1
}

function gotoStudio() {
  if (route.query.from === 'ontology-detail' && route.query.code) {
    router.push(`/ontology/list/${route.query.code}`)
  } else {
    router.push('/ontology/list')
  }
}

onMounted(() => {
  if (!session.value) {
    store.createSession({
      ontologyName: `文件导入-${Date.now().toString(36).slice(-4)}`,
      buildMethod: 'import',
    })
  } else {
    // 复用旧的 drafting 会话时，清空上次残留的解析结果，
    // 避免上一份导入（如宽带退单预置样例）串到本次导入
    store.setActiveSession(session.value.sessionId)
    if (session.value.ontologyObjects.length || session.value.ontologyRelations.length) {
      store.patchActive({ ontologyObjects: [], ontologyRelations: [] })
    }
  }
})
</script>

<style scoped>
.ai-builder { height: 100%; display: flex; flex-direction: column; background: #fafafa; }
.ai-builder__steps { display: flex; align-items: center; justify-content: center; gap: 4px; padding: 16px 24px; background: #fff; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; }
.ai-builder__step { display: flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 12px; color: #999; }
.ai-builder__step--active { color: #4a6fa5; font-weight: 600; }
.ai-builder__step--done { color: #2e7d32; }
.ai-builder__step-num { width: 22px; height: 22px; border-radius: 50%; border: 2px solid currentColor; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }
.ai-builder__step--active .ai-builder__step-num { background: #4a6fa5; color: #fff; border-color: #4a6fa5; }
.ai-builder__step--done .ai-builder__step-num { background: #2e7d32; color: #fff; border-color: #2e7d32; }
.ai-builder__content { flex: 1; overflow-y: auto; }
.ai-builder__loading { display: flex; align-items: center; justify-content: center; height: 100%; color: #999; }
.ai-builder__review, .ai-builder__hydrate { height: 100%; }
</style>
