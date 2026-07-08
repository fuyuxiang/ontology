<template>
  <div class="ai-builder">
    <div v-if="returnPath" class="ai-builder__back-bar">
      <button class="ai-builder__back-btn" @click="router.push(returnPath)">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回对象定义
      </button>
    </div>
    <div class="ai-builder__steps">
      <div v-for="(s, i) in steps" :key="i" class="ai-builder__step" :class="{ 'ai-builder__step--active': step === i, 'ai-builder__step--done': step > i }">
        <div class="ai-builder__step-num">{{ step > i ? '✓' : i + 1 }}</div>
        <div class="ai-builder__step-label">{{ s }}</div>
      </div>
    </div>

    <div class="ai-builder__content">
      <StepDocUpload v-if="step === 0" @next="onUploadDone" />
      <StepDocChat v-else-if="step === 1" :session-id="sessionId" :business-desc="businessDesc" @next="onChatDone" />
      <StepDocMapping v-else-if="step === 2" :session-id="sessionId" :ontology="extractionResult!" @next="onMappingDone" />
      <StepDocMappingPersist v-else-if="step === 3" :session-id="sessionId" :mapping-result="mappedResult!" @prev="step = 2" @next="onPersistDone" />
      <div v-else-if="step === 4" class="ai-builder__review">
        <Step2Review :session="session!" @prev="step = 3" @next="step = 5" />
      </div>
      <div v-else-if="step === 5" class="ai-builder__hydrate">
        <Step3Hydrate :session="session!" @prev="step = 4" @goto-studio="gotoStudio" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBuilderStore } from '../../store/builder'
import StepDocUpload from './components/doc/StepDocUpload.vue'
import StepDocChat from './components/doc/StepDocChat.vue'
import StepDocMapping from './components/doc/StepDocMapping.vue'
import StepDocMappingPersist from './components/doc/StepDocMappingPersist.vue'
import Step2Review from './components/Step2Review.vue'
import Step3Hydrate from './components/Step3Hydrate.vue'

const router = useRouter()
const route = useRoute()
const store = useBuilderStore()
const { sessions, activeSession } = storeToRefs(store)

const returnPath = computed(() => {
  if (route.query.from === 'ontology-detail' && route.query.code) {
    return `/ontology/list/${route.query.code}`
  }
  return ''
})

const steps = ['需求与文档', 'AI对话抽取', '资产映射', '映射确认', '专家审核', '水合验证']
const step = ref(0)
const sessionId = ref('')
const businessDesc = ref('')
const extractionResult = ref<any>(null)
const mappedResult = ref<any>(null)

const session = computed(() => {
  if (activeSession.value && activeSession.value.buildMethod === 'chat') return activeSession.value
  return sessions.value.find(s => s.buildMethod === 'chat' && s.status === 'drafting') || null
})

function onUploadDone(payload: { sessionId: string; businessDesc: string }) {
  sessionId.value = payload.sessionId
  businessDesc.value = payload.businessDesc
  step.value = 1
}

function onChatDone(ontology: any) {
  extractionResult.value = ontology
  step.value = 2
}

function onMappingDone(ontology: any) {
  mappedResult.value = ontology
  step.value = 3
}

function onPersistDone() {
  if (!session.value) {
    store.createSession({ ontologyName: `文档构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat' })
  }
  const ontology = mappedResult.value
  const objects = ontology.entities.map((e: any, i: number) => ({
    id: `obj-${Date.now().toString(36)}-${i}`,
    name: e.name,
    displayName: e.displayName,
    tier: 1 as const,
    namespace: '',
    description: e.description || '',
    primaryKey: 'id',
    icon: '🔷',
    instanceCount: 0,
    table: e.table || undefined,
    tableConfidence: e.confidence || undefined,
    properties: (e.properties || []).map((p: any, j: number) => ({
      id: `prop-${Date.now().toString(36)}-${i}-${j}`,
      name: p.name,
      displayName: p.displayName || p.name,
      type: p.type || 'string',
      required: p.required ?? false,
      field: p.field || undefined,
      fieldType: p.fieldType || undefined,
      fieldConfidence: p.confidence || undefined,
    })),
    derivedProperties: [],
    rules: [],
    actions: [],
    approved: false,
  }))
  const relations = ontology.relations.map((r: any, i: number) => ({
    id: `rel-${Date.now().toString(36)}-${i}`,
    name: r.name,
    displayName: r.displayName,
    source: objects.find((o: any) => o.name === r.source)?.id || r.source,
    target: objects.find((o: any) => o.name === r.target)?.id || r.target,
    cardinality: r.cardinality || '1:N',
    description: r.description || r.displayName,
    relationType: 'ObjectProperty' as const,
    semanticType: 'association' as const,
    sourceField: r.sourceField || undefined,
    sourceTable: r.sourceTable || undefined,
    targetField: r.targetField || undefined,
    targetTable: r.targetTable || undefined,
    mappingConfidence: r.confidence || undefined,
  }))
  store.patchActive({ ontologyObjects: objects, ontologyRelations: relations })
  step.value = 4
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
    store.createSession({ ontologyName: `文档构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat' })
  } else {
    store.setActiveSession(session.value.sessionId)
  }
})
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
.ai-builder__review, .ai-builder__hydrate { height: 100%; }
</style>
