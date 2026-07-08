<template>
  <div class="ai-builder">
    <!-- Step indicator -->
    <div class="ai-builder__steps">
      <div v-for="(s, i) in steps" :key="i" class="ai-builder__step" :class="{ 'ai-builder__step--active': step === i, 'ai-builder__step--done': step > i }">
        <div class="ai-builder__step-num">{{ step > i ? '✓' : i + 1 }}</div>
        <div class="ai-builder__step-label">{{ s }}</div>
      </div>
    </div>

    <!-- Step content -->
    <div class="ai-builder__content">
      <StepBusinessInput v-if="step === 0" @next="onDomainSelected" />
      <StepDomainDrill v-else-if="step === 1" :domains="selectedDomains" :business-desc="businessDesc" @next="onTablesSelected" />
      <StepDocumentPicker v-else-if="step === 2" :business-desc="businessDesc" @next="onDocsSelected" />
      <StepExtraction v-else-if="step === 3" :table-names="selectedTables" :document-keys="selectedDocs" :business-desc="businessDesc" @next="onExtractionDone" />
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
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBuilderStore } from '../../store/builder'
import StepBusinessInput from './components/ai/StepBusinessInput.vue'
import StepDomainDrill from './components/ai/StepDomainDrill.vue'
import StepDocumentPicker from './components/ai/StepDocumentPicker.vue'
import StepExtraction from './components/ai/StepExtraction.vue'
import Step2Review from './components/Step2Review.vue'
import Step3Hydrate from './components/Step3Hydrate.vue'

const router = useRouter()
const route = useRoute()
const store = useBuilderStore()
const { sessions, activeSession } = storeToRefs(store)

const steps = ['业务描述', '选择数据表', '选择文档', 'AI提取', '专家审核', '水合验证']
const step = ref(0)
const businessDesc = ref('')
const selectedDomains = ref<string[]>([])
const selectedTables = ref<string[]>([])
const selectedDocs = ref<string[]>([])

const session = computed(() => {
  if (activeSession.value && activeSession.value.buildMethod === 'chat') return activeSession.value
  return sessions.value.find(s => s.buildMethod === 'chat' && s.status === 'drafting') || null
})

function onDomainSelected(payload: { domains: string[]; businessDesc: string }) {
  selectedDomains.value = payload.domains
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
    store.createSession({ ontologyName: `AI构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat' })
  }
  const assetIds: string[] = result.asset_ids || []
  const objects = result.entities.map((e: any, i: number) => ({
    id: `obj-${Date.now().toString(36)}-${i}`,
    name: e.name,
    displayName: e.displayName,
    tier: 1 as const,
    namespace: '',
    description: e.description || '',
    primaryKey: 'id',
    icon: '🔷',
    instanceCount: 0,
    backing_asset_ids: Array.isArray(e.backing_asset_ids) && e.backing_asset_ids.length
      ? e.backing_asset_ids
      : (assetIds.length ? [...assetIds] : []),
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
  if (!session.value) {
    store.createSession({ ontologyName: `AI构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat' })
  } else {
    store.setActiveSession(session.value.sessionId)
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
.ai-builder__review, .ai-builder__hydrate { height: 100%; }
</style>
