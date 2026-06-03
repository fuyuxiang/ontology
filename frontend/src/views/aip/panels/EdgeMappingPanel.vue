<template>
  <div class="edge-map" v-if="edge">
    <div class="edge-map__header">
      <div class="edge-map__title">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8h12M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        数据映射
      </div>
      <button class="edge-map__close" @click="$emit('close')">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
    </div>

    <div class="edge-map__info">
      <span class="edge-map__node edge-map__node--src">{{ sourceLabel }}</span>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 8h8M9 5l3 3-3 3" stroke="#94a3b8" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span class="edge-map__node edge-map__node--tgt">{{ targetLabel }}</span>
    </div>

    <div class="edge-map__body">
      <div class="edge-map__col">
        <div class="edge-map__col-title">上游输出字段</div>
        <div
          v-for="field in sourceFields"
          :key="field"
          class="edge-map__field edge-map__field--src"
          draggable="true"
          @dragstart="onDragStart(field, $event)"
        >
          <span class="edge-map__dot edge-map__dot--blue"></span>
          {{ field }}
        </div>
        <div v-if="!sourceFields.length" class="edge-map__empty">暂无输出 schema</div>
      </div>

      <div class="edge-map__arrow-col">
        <svg v-for="(m, i) in mappings" :key="i" width="24" height="20" viewBox="0 0 24 20">
          <path d="M4 10h16M16 6l4 4-4 4" stroke="#2E5BFF" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>

      <div class="edge-map__col">
        <div class="edge-map__col-title">下游输入参数</div>
        <div
          v-for="field in targetFields"
          :key="field"
          class="edge-map__field edge-map__field--tgt"
          @dragover.prevent
          @drop="onDrop(field, $event)"
          :class="{ 'edge-map__field--mapped': isMapped(field) }"
        >
          <span class="edge-map__dot edge-map__dot--green"></span>
          {{ field }}
          <span v-if="getMappedSource(field)" class="edge-map__mapped-from">← {{ getMappedSource(field) }}</span>
        </div>
        <div v-if="!targetFields.length" class="edge-map__empty">暂无输入 schema</div>
      </div>
    </div>

    <div class="edge-map__section-label">映射列表</div>
    <div class="edge-map__list">
      <div v-for="(m, i) in mappings" :key="i" class="edge-map__row">
        <input class="edge-map__input" v-model="m.source_field" placeholder="上游字段路径" @input="save" />
        <svg width="16" height="16" viewBox="0 0 16 16"><path d="M4 8h8M9 5l3 3-3 3" stroke="#64748b" stroke-width="1.5" stroke-linecap="round"/></svg>
        <input class="edge-map__input" v-model="m.target_field" placeholder="下游参数名" @input="save" />
        <button class="edge-map__del" @click="removeMapping(i)">×</button>
      </div>
      <button class="edge-map__add" @click="addMapping">+ 添加映射</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAipStore } from '../../../store/aip'
import { NODE_TYPES } from '../aipData'

const props = defineProps<{ edgeId: string | null }>()
const emit = defineEmits<{ close: [] }>()

const store = useAipStore()

const edge = computed(() => {
  if (!props.edgeId || !store.currentScene) return null
  return (store.currentScene.edges_json || []).find((e: any) => e.id === props.edgeId)
})

const sourceNode = computed(() => {
  if (!edge.value || !store.currentScene) return null
  return (store.currentScene.nodes_json || []).find((n: any) => n.id === edge.value!.source)
})

const targetNode = computed(() => {
  if (!edge.value || !store.currentScene) return null
  return (store.currentScene.nodes_json || []).find((n: any) => n.id === edge.value!.target)
})

const sourceLabel = computed(() => sourceNode.value?.data?.label || edge.value?.source || '')
const targetLabel = computed(() => targetNode.value?.data?.label || edge.value?.target || '')

const sourceFields = computed(() => inferOutputFields(sourceNode.value))
const targetFields = computed(() => inferInputFields(targetNode.value))

const mappings = ref<Array<{ source_field: string; target_field: string }>>([])

watch(() => edge.value, (e) => {
  if (e) {
    const data = e.data || {}
    mappings.value = [...(data.mapping || [])]
  } else {
    mappings.value = []
  }
}, { immediate: true })

function save() {
  if (!edge.value || !store.currentScene) return
  if (!edge.value.data) edge.value.data = {}
  edge.value.data.mapping = [...mappings.value]
  store.markDirty()
}

function addMapping() {
  mappings.value.push({ source_field: '', target_field: '' })
  save()
}

function removeMapping(index: number) {
  mappings.value.splice(index, 1)
  save()
}

function isMapped(targetField: string) {
  return mappings.value.some(m => m.target_field === targetField)
}

function getMappedSource(targetField: string) {
  const m = mappings.value.find(m => m.target_field === targetField)
  return m?.source_field || ''
}

let dragField = ''
function onDragStart(field: string, e: DragEvent) {
  dragField = field
  e.dataTransfer?.setData('text/plain', field)
}

function onDrop(targetField: string, e: DragEvent) {
  e.preventDefault()
  const srcField = e.dataTransfer?.getData('text/plain') || dragField
  if (!srcField) return
  const existing = mappings.value.findIndex(m => m.target_field === targetField)
  if (existing >= 0) {
    mappings.value[existing].source_field = srcField
  } else {
    mappings.value.push({ source_field: srcField, target_field: targetField })
  }
  save()
}

function inferOutputFields(node: any): string[] {
  if (!node) return []
  const t = node.type
  if (t === 'ontologyQuery') return ['data', 'data[0]', 'count', 'entity_name']
  if (t === 'ruleEngine') return ['triggered', 'matched_count', 'confidence', 'risk_level']
  if (t === 'llmAgent') return ['answer']
  if (t === 'agentNode') return ['answer', 'rounds']
  if (t === 'function') return ['value', 'function']
  if (t === 'datasource') return ['rows', 'rows[0]', 'row_count']
  if (t === 'condition') return ['branch', 'actual', 'expected']
  if (t === 'httpCall') return ['status_code', 'body']
  if (t === 'writebackOntology') return ['written', 'target', 'row']
  if (t === 'actionSystem') return ['success', 'message', 'effects']
  if (t === 'loop') return ['items', 'item_count']
  return ['output']
}

function inferInputFields(node: any): string[] {
  if (!node) return []
  const t = node.type
  if (t === 'ontologyQuery') return ['objectType', 'filters']
  if (t === 'ruleEngine') return ['user_id', 'rule_name']
  if (t === 'llmAgent') return ['prompt', 'context']
  if (t === 'agentNode') return ['input_data']
  if (t === 'function') return Object.keys(node.data?.params || {}).length ? Object.keys(node.data.params) : ['params']
  if (t === 'datasource') return ['sql', 'datasource_name']
  if (t === 'condition') return ['field', 'value']
  if (t === 'httpCall') return ['url', 'body']
  if (t === 'writebackOntology') return ['target_ontology', 'mapping']
  if (t === 'actionSystem') return ['action_id', 'params']
  if (t === 'subscene') return ['input_params']
  return ['input']
}
</script>

<style scoped>
.edge-map { padding: 16px; height: 100%; display: flex; flex-direction: column; overflow-y: auto; }
.edge-map__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.edge-map__title { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; color: #1e293b; }
.edge-map__close { border: none; background: none; cursor: pointer; color: #94a3b8; padding: 4px; border-radius: 4px; }
.edge-map__close:hover { background: #f1f5f9; color: #475569; }

.edge-map__info { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f8fafc; border-radius: 6px; margin-bottom: 16px; }
.edge-map__node { font-size: 12px; font-weight: 500; padding: 2px 8px; border-radius: 4px; }
.edge-map__node--src { background: #dbeafe; color: #1d4ed8; }
.edge-map__node--tgt { background: #dcfce7; color: #166534; }

.edge-map__body { display: flex; gap: 8px; margin-bottom: 16px; flex: 1; min-height: 0; }
.edge-map__col { flex: 1; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px; overflow-y: auto; }
.edge-map__col-title { font-size: 10px; text-transform: uppercase; color: #94a3b8; margin-bottom: 6px; font-weight: 600; }
.edge-map__arrow-col { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; width: 32px; }

.edge-map__field { display: flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: #475569; cursor: grab; margin-bottom: 3px; border: 1px solid transparent; transition: all .15s; }
.edge-map__field--src:hover { background: #eff6ff; border-color: #bfdbfe; }
.edge-map__field--tgt { cursor: default; }
.edge-map__field--tgt:hover { background: #f0fdf4; border-color: #bbf7d0; }
.edge-map__field--mapped { background: #f0fdf4; border-color: #86efac; }
.edge-map__dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.edge-map__dot--blue { background: #3b82f6; }
.edge-map__dot--green { background: #10b981; }
.edge-map__mapped-from { font-size: 10px; color: #2E5BFF; margin-left: auto; }
.edge-map__empty { font-size: 11px; color: #94a3b8; padding: 8px; text-align: center; }

.edge-map__section-label { font-size: 10px; text-transform: uppercase; color: #94a3b8; margin-bottom: 6px; font-weight: 600; }
.edge-map__list { margin-bottom: 12px; }
.edge-map__row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.edge-map__input { flex: 1; padding: 4px 8px; font-size: 11px; border: 1px solid #e2e8f0; border-radius: 4px; outline: none; }
.edge-map__input:focus { border-color: #2E5BFF; box-shadow: 0 0 0 2px rgba(46, 91, 255, .1); }
.edge-map__del { border: none; background: none; color: #ef4444; cursor: pointer; font-size: 14px; padding: 2px 6px; border-radius: 4px; }
.edge-map__del:hover { background: #fef2f2; }
.edge-map__add { border: 1px dashed #cbd5e1; background: none; color: #64748b; padding: 4px 12px; border-radius: 4px; font-size: 11px; cursor: pointer; width: 100%; }
.edge-map__add:hover { border-color: #2E5BFF; color: #2E5BFF; }
</style>
