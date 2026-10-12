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
    <!-- Step indicator -->
    <div class="ai-builder__steps">
      <div v-for="(s, i) in steps" :key="i" role="button" :tabindex="i <= step ? 0 : -1" @click="i <= step && (step = i)" @keydown.enter="i <= step && (step = i)" class="ai-builder__step" :class="{ 'ai-builder__step--active': step === i, 'ai-builder__step--done': step > i }">
        <div class="ai-builder__step-num">{{ step > i ? '✓' : i + 1 }}</div>
        <div class="ai-builder__step-label">{{ s }}</div>
      </div>
    </div>

    <!-- Step content -->
    <div v-if="targetOntologyId" :key="targetOntologyId" class="ai-builder__content">
      <StepBusinessInput v-if="step === 0" :initial-desc="businessDesc" @next="onBusinessEntered" />
      <StepAssetPicker v-else-if="step === 1" :business-desc="businessDesc" :initial-selected="selectedTables" @next="onTablesSelected" />
      <StepDocumentPicker v-else-if="step === 2" :business-desc="businessDesc" :initial-selected="selectedDocs" @next="onDocsSelected" />
      <StepExtraction v-else-if="step === 3" :table-names="selectedTables" :document-keys="selectedDocs" :business-desc="businessDesc" @next="onExtractionDone" @retry="step = 2" />
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
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../../store/auth'
import { matchesBuilderSession } from '../../utils/builderSession'
import BuilderTargetSelector from './components/BuilderTargetSelector.vue'
import { useBuilderStore } from '../../store/builder'
import StepBusinessInput from './components/ai/StepBusinessInput.vue'
import StepAssetPicker from './components/ai/StepAssetPicker.vue'
import StepDocumentPicker from './components/ai/StepDocumentPicker.vue'
import StepExtraction from './components/ai/StepExtraction.vue'
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

const steps = computed(() => ['业务描述', '选择数据表', '选择文档', 'AI提取', '数据映射', '最终审核', '水合验证'].map(value => text(value)))
const step = ref(0)
const businessDesc = ref('')
const selectedTables = ref<string[]>([])
const selectedDocs = ref<string[]>([])

const session = computed(() => {
  const matches = (draft: import('../../types/builder').BuilderSession) =>
    matchesBuilderSession(draft, 'asset', targetOntologyId.value, auth.user?.id)
  if (activeSession.value && matches(activeSession.value)) return activeSession.value
  return sessions.value.find(draft => matches(draft) && draft.status !== 'published') || null
})

function onBusinessEntered(payload: { businessDesc: string }) {
  businessDesc.value = payload.businessDesc
  step.value = 1
}

function onTablesSelected(tables: string[]) {
  selectedTables.value = tables
  step.value = 2
}

function onDocsSelected(keys: string[]) {
  selectedDocs.value = keys
  step.value = 3
}

function onExtractionDone(result: any) {
  if (!session.value) {
    store.createSession({ ontologyName: `AI构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat', ontologyId: targetOntologyId.value, builderKind: 'asset' })
  }
  const assetIds: string[] = result.asset_ids || []
  const objects = result.entities.map((e: any, i: number) => ({
    id: `obj-${Date.now().toString(36)}-${i}`,
    name: e.name,
    displayName: e.displayName,
    tier: 1 as const,
    namespace: '',
    description: e.description || '',
    primaryKey: e.primaryKey || 'id',
    icon: '🔷',
    instanceCount: 0,
    backing_asset_ids: Array.isArray(e.backing_asset_ids) && e.backing_asset_ids.length
      ? e.backing_asset_ids
      : [],
    properties: (e.properties || []).map((p: any, j: number) => ({
      id: `prop-${Date.now().toString(36)}-${i}-${j}`,
      name: p.name,
      displayName: p.displayName || p.name,
      type: p.type || 'string',
      required: p.required ?? false,
      source_asset_id: p.source_asset_id ?? null,
      source_column: p.source_column ?? p.source_field ?? null,
      source_field: p.source_field ?? null,
      source_table: p.source_table ?? null,
    })),
    derivedProperties: [],
    rules: [],
    actions: [],
    approved: false,
  }))
  const relations = result.relations.map((r: any, i: number) => ({
    id: `rel-${Date.now().toString(36)}-${i}`,
    name: r.name,
    displayName: r.displayName,
    source: objects.find((o: any) => o.name === r.source)?.id || r.source,
    target: objects.find((o: any) => o.name === r.target)?.id || r.target,
    cardinality: r.cardinality || '1:N',
    description: r.description || r.displayName,
    relationType: 'ObjectProperty' as const,
    semanticType: 'association' as const,
    sourceField: r.sourceField || r.source_field, targetField: r.targetField || r.target_field,
  }))
  store.patchActive({ ontologyObjects: objects, ontologyRelations: relations, selectedAssetIds: assetIds })
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
    store.createSession({ ontologyName: `AI构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat', ontologyId: targetOntologyId.value, builderKind: 'asset' })
  } else {
    store.setActiveSession(session.value.sessionId)
  }
  if (saved?.step !== undefined) step.value = saved.workflowVersion === 2 ? saved.step : (saved.step === 4 || saved.step === 5 ? 4 : saved.step)
  if (saved?.businessDesc !== undefined) businessDesc.value = saved.businessDesc
  if (saved?.selectedTables !== undefined) selectedTables.value = saved.selectedTables
  if (saved?.selectedDocs !== undefined) selectedDocs.value = saved.selectedDocs
})
watch(targetOntologyId, () => {
  if (!targetOntologyId.value) return
  if (!session.value) store.createSession({ ontologyName: 'asset构建', buildMethod: 'chat', ontologyId: targetOntologyId.value, builderKind: 'asset' })
  else store.setActiveSession(session.value.sessionId)
  const saved = session.value?.builderState
  step.value = saved?.workflowVersion === 2 ? (saved.step || 0) : (saved?.step === 4 || saved?.step === 5 ? 4 : saved?.step || 0)
  businessDesc.value = saved?.businessDesc || ''; selectedTables.value = saved?.selectedTables || []; selectedDocs.value = saved?.selectedDocs || []
})
watch([step, businessDesc, selectedTables, selectedDocs], () => {
  if (!session.value) return
  store.updateSession(session.value.sessionId, { builderState: { workflowVersion: 2, step: step.value, businessDesc: businessDesc.value, selectedTables: selectedTables.value, selectedDocs: selectedDocs.value } })
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
