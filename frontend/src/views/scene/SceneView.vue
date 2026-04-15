<template>
  <div class="scene">
    <div v-if="!hideHeader" class="scene__header">
      <div class="scene__title-row">
        <div class="scene__icon" :style="{ background: config.color }">
          <span v-html="config.icon"></span>
        </div>
        <div>
          <h1 class="text-display">{{ config.title }}</h1>
          <p class="text-caption" style="margin-top: 4px;">{{ config.description }}</p>
        </div>
      </div>
    </div>

    <PageState :loading="loading" :empty="!loading && entities.length === 0" text="Loading..." empty-text="No data">

    <!-- KPI -->
    <div class="scene__kpis">
      <div class="scene__kpi" v-for="kpi in kpis" :key="kpi.label">
        <div class="scene__kpi-value">{{ kpi.value }}</div>
        <div class="scene__kpi-label">{{ kpi.label }}</div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="scene__tabs">
      <button v-for="tab in tabs" :key="tab" class="scene__tab" :class="{ 'scene__tab--active': activeTab === tab }" @click="activeTab = tab">{{ tab }}</button>
    </div>

    <!-- Objects -->
    <div v-if="activeTab === tabs[0]" class="scene__objects">
      <div v-for="e in entities" :key="e.id" class="scene__obj-card" @click="selectedId = selectedId === e.id ? null : e.id">
        <span class="scene__obj-badge" :style="{ background: `var(--tier${e.tier}-primary)` }">T{{ e.tier }}</span>
        <div class="scene__obj-info">
          <span class="scene__obj-name">{{ e.name }}</span>
          <span class="scene__obj-cn">{{ e.name_cn }}</span>
        </div>
        <span class="scene__obj-count">{{ e.attr_count }} attrs</span>
      </div>
    </div>

    <!-- Relations -->
    <div v-else-if="activeTab === tabs[1]" class="scene__relations">
      <div v-for="(r, i) in relations" :key="i" class="scene__rel-card">
        <span class="scene__rel-from">{{ r.from_entity_name }}</span>
        <div class="scene__rel-arrow">
          <span class="scene__rel-label">{{ r.name }}</span>
          <span class="scene__rel-card-type">{{ r.cardinality }}</span>
        </div>
        <span class="scene__rel-to">{{ r.to_entity_name }}</span>
      </div>
      <div v-if="relations.length === 0" class="scene__empty">No relations</div>
    </div>

    <!-- Detail -->
    <div v-else-if="activeTab === tabs[2]" class="scene__detail-tab">
      <div v-if="!detail" class="scene__empty">Select an object from the list above</div>
      <template v-else>
        <h3 class="text-h2" style="margin-bottom: 12px;">{{ detail.name }} <span style="color:var(--neutral-500);font-weight:400;">{{ detail.name_cn }}</span></h3>
        <p class="text-caption" style="margin-bottom: 16px;">{{ detail.description }}</p>
        <table class="scene__table">
          <thead><tr><th>Name</th><th>Type</th><th>Description</th><th>Required</th></tr></thead>
          <tbody>
            <tr v-for="a in detail.attributes" :key="a.id">
              <td><code>{{ a.name }}</code></td>
              <td><span class="type-tag">{{ a.type }}</span></td>
              <td>{{ a.description }}</td>
              <td><span class="dot" :class="a.required ? 'dot--yes' : 'dot--no'"></span></td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>

    </PageState>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import PageState from '../../components/common/PageState.vue'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import type { EntityListItem, OntologyEntity } from '../../types'
import type { RelationData } from '../../api/relations'

interface SceneConfig {
  namespace: string; title: string; description: string; color: string; icon: string
}

const props = defineProps<{ config: SceneConfig; hideHeader?: boolean }>()

const loading = ref(true)
const entities = ref<EntityListItem[]>([])
const relations = ref<RelationData[]>([])
const selectedId = ref<string | null>(null)
const detail = ref<OntologyEntity | null>(null)
const activeTab = ref('Objects')
const tabs = ['Objects', 'Relations', 'Detail']

const kpis = computed(() => [
  { label: 'Objects', value: entities.value.length },
  { label: 'Relations', value: relations.value.length },
  { label: 'Attributes', value: entities.value.reduce((s, e) => s + e.attr_count, 0) },
])

onMounted(async () => {
  loading.value = true
  try {
    entities.value = await entityApi.list({ namespace: props.config.namespace })
    // Load relations for all entities in this namespace
    const allRels: RelationData[] = []
    for (const e of entities.value) {
      const rels = await relationApi.list(e.id)
      for (const r of rels) {
        if (!allRels.find(x => x.id === r.id)) allRels.push(r)
      }
    }
    relations.value = allRels
  } finally {
    loading.value = false
  }
})

watch(selectedId, async (id) => {
  if (id) {
    detail.value = await entityApi.detail(id)
    activeTab.value = 'Detail'
  } else {
    detail.value = null
  }
})
</script>

<style scoped>
.scene { padding: 24px; }
.scene__header { margin-bottom: 20px; }
.scene__title-row { display: flex; align-items: center; gap: 16px; }
.scene__icon { width: 48px; height: 48px; border-radius: var(--radius-xl); display: flex; align-items: center; justify-content: center; color: #fff; }

.scene__kpis { display: flex; gap: 12px; margin-bottom: 20px; }
.scene__kpi { flex: 1; padding: 16px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); text-align: center; }
.scene__kpi-value { font-size: 28px; font-weight: 700; color: var(--neutral-900); }
.scene__kpi-label { font-size: 11px; color: var(--neutral-600); text-transform: uppercase; letter-spacing: 0.3px; margin-top: 4px; }

.scene__tabs { display: flex; border-bottom: 2px solid var(--neutral-200); margin-bottom: 16px; }
.scene__tab { padding: 8px 16px; font-size: 13px; font-weight: 500; color: var(--neutral-600); background: transparent; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; }
.scene__tab:hover { color: var(--neutral-800); }
.scene__tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-600); }

.scene__objects { display: flex; flex-wrap: wrap; gap: 10px; }
.scene__obj-card { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); background: var(--neutral-0); cursor: pointer; transition: all 200ms ease; min-width: 200px; }
.scene__obj-card:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); border-color: var(--semantic-300); }
.scene__obj-badge { width: 22px; height: 22px; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #fff; flex-shrink: 0; }
.scene__obj-info { flex: 1; display: flex; flex-direction: column; }
.scene__obj-name { font-size: 13px; font-weight: 500; color: var(--neutral-800); }
.scene__obj-cn { font-size: 11px; color: var(--neutral-500); }
.scene__obj-count { font-size: 10px; color: var(--neutral-400); }

.scene__relations { display: flex; flex-direction: column; gap: 6px; }
.scene__rel-card { display: flex; align-items: center; gap: 12px; padding: 8px 14px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); }
.scene__rel-from, .scene__rel-to { font-size: 12px; font-weight: 500; color: var(--neutral-800); padding: 3px 8px; background: var(--neutral-50); border-radius: var(--radius-sm); }
.scene__rel-arrow { flex: 1; display: flex; flex-direction: column; align-items: center; position: relative; min-width: 60px; }
.scene__rel-arrow::before { content: ''; position: absolute; top: 50%; left: 0; right: 0; height: 1px; background: var(--semantic-300); }
.scene__rel-arrow::after { content: ''; position: absolute; top: 50%; right: 0; transform: translateY(-50%); border: 4px solid transparent; border-left-color: var(--semantic-300); }
.scene__rel-label { font-size: 10px; font-weight: 500; color: var(--neutral-700); background: var(--neutral-0); padding: 0 4px; position: relative; z-index: 1; }
.scene__rel-card-type { font-size: 10px; color: var(--neutral-500); background: var(--neutral-50); padding: 1px 5px; border-radius: 3px; position: relative; z-index: 1; }

.scene__detail-tab { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 20px; }
.scene__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.scene__table th { text-align: left; padding: 8px 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; color: var(--neutral-500); border-bottom: 1px solid var(--neutral-200); }
.scene__table td { padding: 10px 12px; color: var(--neutral-700); border-bottom: 1px solid var(--neutral-100); }
.scene__table tr:hover td { background: var(--semantic-50); }
.type-tag { display: inline-block; padding: 1px 7px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 500; background: var(--neutral-100); color: var(--neutral-700); font-family: var(--font-mono); }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; }
.dot--yes { background: var(--status-success); }
.dot--no { background: var(--neutral-300); }
.scene__empty { padding: 40px; text-align: center; color: var(--neutral-400); font-size: 13px; }
</style>
