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
      <StepDocUpload v-if="step === 0" @next="onUploadDone" />
      <StepDocChat v-else-if="step === 1" :session-id="sessionId" :business-desc="businessDesc" @next="onChatDone" />
      <StepDocMapping v-else-if="step === 2" :session-id="sessionId" :ontology="extractionResult!" @next="onMappingDone" />
      <StepDocMappingPersist v-else-if="step === 3" :session-id="sessionId" :mapping-result="mappedResult!" @prev="step = 2" @next="onPersistDone" />
      <Step3Mapping v-else-if="step === 4" :session="session!" @prev="step = 3" @next="step = 5" />
      <div v-else-if="step === 5" class="ai-builder__review">
        <Step2Review :session="session!" :mapping-complete="true" @prev="step = 4" @next="step = 6" />
      </div>
      <div v-else-if="step === 6" class="ai-builder__hydrate">
        <Step3Hydrate :session="session!" @prev="step = 5" @goto-studio="gotoStudio" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../../store/auth'
import { matchesBuilderSession } from '../../utils/builderSession'
import BuilderTargetSelector from './components/BuilderTargetSelector.vue'
import { useBuilderStore } from '../../store/builder'
import StepDocUpload from './components/doc/StepDocUpload.vue'
import StepDocChat from './components/doc/StepDocChat.vue'
import StepDocMapping from './components/doc/StepDocMapping.vue'
import StepDocMappingPersist from './components/doc/StepDocMappingPersist.vue'
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

const steps = computed(() => ['需求与文档', 'AI对话抽取', '资产映射', '映射确认', '字段确认', '最终审核', '水合验证'].map(value => text(value)))
const step = ref(0)
const sessionId = ref('')
const businessDesc = ref('')
const extractionResult = ref<any>(null)
const mappedResult = ref<any>(null)

const session = computed(() => {
  const matches = (draft: import('../../types/builder').BuilderSession) =>
    matchesBuilderSession(draft, 'document', targetOntologyId.value, auth.user?.id)
  if (activeSession.value && matches(activeSession.value)) return activeSession.value
  return sessions.value.find(draft => matches(draft) && draft.status !== 'published') || null
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

function onPersistDone(items: import('../../api/docBuilder').MappingPreviewItem[]) {
  if (!session.value) {
    store.createSession({ ontologyName: `文档构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat', ontologyId: targetOntologyId.value, builderKind: 'document' })
  }
  const ontology = mappedResult.value
  const objects = items.map((item, i) => {
    const entity = ontology.entities?.find((candidate: any) => candidate.name === item.entity_name) || {}
    return {
      id: item.entity_id || `obj-${Date.now().toString(36)}-${i}`,
      name: item.entity_name,
      displayName: entity.displayName || item.entity_name,
      tier: (entity.tier || 3) as 1 | 2 | 3,
      namespace: '', description: entity.description || '',
      primaryKey: item.primary_key || entity.primaryKey || 'id',
      icon: '🔷', instanceCount: 0,
      backing_asset_ids: item.backing_asset_ids || (item.asset_id ? [item.asset_id] : []),
      enrichment_bindings: item.enrichment_bindings || [],
      table: item.table_name || undefined,
      properties: item.field_mappings.map((mapping, j) => {
        const property = entity.properties?.find((candidate: any) => candidate.name === mapping.attribute_name) || {}
        return {
          id: mapping.attribute_id || `prop-${Date.now().toString(36)}-${i}-${j}`,
          name: mapping.attribute_name, displayName: property.displayName || mapping.attribute_name,
          type: mapping.type || property.type || 'string', required: mapping.required ?? property.required ?? false,
          description: mapping.description ?? property.description ?? '',
          source_asset_id: mapping.source_asset_id !== undefined ? mapping.source_asset_id : item.asset_id ?? null,
          source_column: mapping.source_column, source_field: mapping.source_column,
          source_table: item.table_name, transform: mapping.transform ?? null,
          field: mapping.source_column || undefined, fieldConfidence: mapping.confidence,
        }
      }),
      derivedProperties: [], rules: [], actions: [], approved: false,
    }
  })
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
  store.patchActive({ ontologyObjects: objects, ontologyRelations: relations, documentSessionId: sessionId.value })
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
  const saved = session.value?.builderState
  if (!session.value) {
    store.createSession({ ontologyName: `文档构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat', ontologyId: targetOntologyId.value, builderKind: 'document' })
  } else {
    store.setActiveSession(session.value.sessionId)
  }
  if (saved?.step !== undefined) step.value = saved.workflowVersion === 2 ? saved.step : (saved.step === 4 || saved.step === 5 ? 4 : saved.step)
  if (saved?.sessionId !== undefined) sessionId.value = saved.sessionId
  if (saved?.businessDesc !== undefined) businessDesc.value = saved.businessDesc
  if (saved?.extractionResult !== undefined) extractionResult.value = saved.extractionResult
  if (saved?.mappedResult !== undefined) mappedResult.value = saved.mappedResult
})
watch(targetOntologyId, () => {
  if (!targetOntologyId.value) return
  if (!session.value) store.createSession({ ontologyName: 'document构建', buildMethod: 'chat', ontologyId: targetOntologyId.value, builderKind: 'document' })
  else store.setActiveSession(session.value.sessionId)
  const saved = session.value?.builderState
  step.value = saved?.workflowVersion === 2 ? (saved.step || 0) : (saved?.step === 4 || saved?.step === 5 ? 4 : saved?.step || 0)
  sessionId.value = saved?.sessionId || ''; businessDesc.value = saved?.businessDesc || ''; extractionResult.value = saved?.extractionResult || null; mappedResult.value = saved?.mappedResult || null
})
watch([step, sessionId, businessDesc, extractionResult, mappedResult], () => {
  if (!session.value) return
  store.updateSession(session.value.sessionId, { builderState: { workflowVersion: 2, step: step.value, sessionId: sessionId.value, businessDesc: businessDesc.value, extractionResult: extractionResult.value, mappedResult: mappedResult.value } })
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
.ai-builder__review, .ai-builder__hydrate { height: 100%; }
@media (max-width: 768px) { .ai-builder__steps { flex-wrap: wrap; padding: 12px 8px; justify-content: flex-start; gap: 8px; } .ai-builder__step { padding: 4px 6px; } .ai-builder__step-label { white-space: nowrap; } }
</style>
