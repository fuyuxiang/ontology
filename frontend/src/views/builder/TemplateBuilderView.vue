<template>
  <div class="ai-builder">
    <BuilderTargetSelector />
    <div v-if="returnPath" class="ai-builder__back-bar">
      <button class="ai-builder__back-btn" @click="router.push(returnPath)">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ text('返回对象定义') }}
      </button>
    </div>
    <div class="ai-builder__steps">
      <div v-for="(s, i) in steps" :key="i" role="button" :tabindex="i <= step ? 0 : -1" @click="i <= step && (step = i)" @keydown.enter="i <= step && (step = i)" class="ai-builder__step" :class="{ 'ai-builder__step--active': step === i, 'ai-builder__step--done': step > i }">
        <div class="ai-builder__step-num">{{ step > i ? '✓' : i + 1 }}</div>
        <div class="ai-builder__step-label">{{ s }}</div>
      </div>
    </div>

    <div v-if="targetOntologyId" :key="targetOntologyId" class="ai-builder__content">
      <div v-if="!session" class="ai-builder__loading">正在初始化…</div>
      <Step1Import v-else-if="step === 0" :session="session" @next="onImportDone" />
      <Step3Mapping v-else-if="step === 1" :session="session!" @prev="step = 0" @next="step = 2" />
      <div v-else-if="step === 2" class="ai-builder__review">
        <Step2Review :session="session!" :mapping-complete="true" @prev="step = 1" @next="step = 3" />
      </div>
      <div v-else-if="step === 3" class="ai-builder__hydrate">
        <Step3Hydrate :session="session!" @prev="step = 2" @goto-studio="gotoStudio" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../../store/auth'
import { matchesBuilderSession } from '../../utils/builderSession'
import BuilderTargetSelector from './components/BuilderTargetSelector.vue'
import { useBuilderStore } from '../../store/builder'
import Step1Import from './components/Step1Import.vue'
import Step2Review from './components/Step2Review.vue'
import Step3Hydrate from './components/Step3Hydrate.vue'
import Step3Mapping from './components/Step3Mapping.vue'

const router = useRouter()
const route = useRoute()
const store = useBuilderStore()
const auth = useAuthStore()
const targetOntologyId = computed(() => (route.query.ontology_id as string) || undefined)
const { sessions, activeSession } = storeToRefs(store)

const returnPath = computed(() => {
  if (route.query.from === 'ontology-detail' && route.query.code) {
    return `/ontology/list/${route.query.code}`
  }
  return ''
})

const steps = computed(() => ['文件导入', '数据映射', '最终审核', '水合验证'].map(value => text(value)))
const step = ref(0)

const session = computed(() => {
  const matches = (draft: import('../../types/builder').BuilderSession) =>
    matchesBuilderSession(draft, 'import', targetOntologyId.value, auth.user?.id)
  if (activeSession.value && matches(activeSession.value)) return activeSession.value
  return sessions.value.find(draft => matches(draft) && draft.status !== 'published') || null
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
  const saved = session.value?.builderState
  if (!session.value) {
    store.createSession({
      ontologyName: `文件导入-${Date.now().toString(36).slice(-4)}`,
      buildMethod: 'import', ontologyId: targetOntologyId.value, builderKind: 'import',
    })
  } else {
    store.setActiveSession(session.value.sessionId)
  }
  if (saved?.step !== undefined) step.value = saved.workflowVersion === 2 ? saved.step : (saved.step === 1 || saved.step === 2 ? 1 : saved.step)
})
watch(targetOntologyId, () => {
  if (!targetOntologyId.value) return
  if (!session.value) store.createSession({ ontologyName: 'import构建', buildMethod: 'import', ontologyId: targetOntologyId.value, builderKind: 'import' })
  else store.setActiveSession(session.value.sessionId)
  const saved = session.value?.builderState
  step.value = saved?.workflowVersion === 2 ? (saved.step || 0) : (saved?.step === 1 || saved?.step === 2 ? 1 : saved?.step || 0)

})
watch([step], () => {
  if (!session.value) return
  store.updateSession(session.value.sessionId, { builderState: { workflowVersion: 2, step: step.value } })
}, { deep: true })
</script>

<style scoped>
.ai-builder { height: 100%; display: flex; flex-direction: column; background: #fafafa; }
.ai-builder__back-bar { padding: 10px 24px; background: #fff; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; }
.ai-builder__back-btn { display: flex; align-items: center; gap: 4px; padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; color: #334155; font-size: 13px; cursor: pointer; transition: background 0.15s; }
.ai-builder__back-btn:hover { background: #f8fafc; }
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
@media (max-width: 768px) { .ai-builder__steps { flex-wrap: wrap; padding: 12px 8px; justify-content: flex-start; gap: 8px; } .ai-builder__step { padding: 4px 6px; } .ai-builder__step-label { white-space: nowrap; } }
</style>
