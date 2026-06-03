<template>
  <div class="ai-builder">
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
      <StepDocReview v-else-if="step === 3" :result="mappedResult!" @prev="step = 2" @confirm="onConfirm" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBuilderStore } from '../../store/builder'
import StepDocUpload from './components/doc/StepDocUpload.vue'
import StepDocChat from './components/doc/StepDocChat.vue'
import StepDocMapping from './components/doc/StepDocMapping.vue'
import StepDocReview from './components/doc/StepDocReview.vue'

const router = useRouter()
const store = useBuilderStore()

const steps = ['需求与文档', 'AI对话抽取', '资产映射', '确认入库']
const step = ref(0)
const sessionId = ref('')
const businessDesc = ref('')
const extractionResult = ref<any>(null)
const mappedResult = ref<any>(null)

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

function onConfirm(ontology: any) {
  store.createSession({ ontologyName: `文档构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat' })
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
  router.push('/studio')
}
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
</style>
