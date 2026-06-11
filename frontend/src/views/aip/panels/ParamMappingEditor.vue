<template>
  <div class="pm-editor">
    <div v-for="param in params" :key="param.name" class="pm-row">
      <label class="pm-label">{{ param.name }} <span class="pm-type">({{ param.type }})</span></label>
      <div class="pm-source">
        <select v-model="localMapping[param.name].source" class="aip-input pm-select" @change="emitUpdate">
          <option value="node">上游节点</option>
          <option value="variable">流程变量</option>
          <option value="expression">表达式</option>
        </select>
        <template v-if="localMapping[param.name].source === 'node'">
          <select v-model="localMapping[param.name].node_id" class="aip-input" @change="emitUpdate">
            <option value="">选择节点</option>
            <option v-for="n in upstreamNodes" :key="n.id" :value="n.id">{{ n.data?.label || n.id }}</option>
          </select>
          <input v-model="localMapping[param.name].field" class="aip-input" placeholder="output.field" @input="emitUpdate" />
        </template>
        <template v-else-if="localMapping[param.name].source === 'variable'">
          <input v-model="localMapping[param.name].var_name" class="aip-input" placeholder="变量名" @input="emitUpdate" />
        </template>
        <template v-else>
          <input v-model="localMapping[param.name].expr" class="aip-input" placeholder="{{nodes.x.output.y}}" @input="emitUpdate" />
        </template>
      </div>
    </div>
    <div v-if="!params.length" class="pm-empty">该组件无输入参数</div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

interface Param {
  name: string
  type: string
  required?: boolean
}

interface MappingEntry {
  source: string
  node_id?: string
  field?: string
  var_name?: string
  expr?: string
}

const props = defineProps<{
  params: Param[]
  modelValue: Record<string, MappingEntry>
  upstreamNodes: Array<{ id: string; data?: Record<string, any> }>
}>()

const emit = defineEmits<{ (e: 'update:modelValue', v: Record<string, MappingEntry>): void }>()

const localMapping = reactive<Record<string, MappingEntry>>({})

watch(() => props.params, (ps) => {
  for (const p of ps) {
    if (!localMapping[p.name]) {
      localMapping[p.name] = props.modelValue?.[p.name] || { source: 'variable', var_name: '' }
    }
  }
}, { immediate: true })

function emitUpdate() {
  emit('update:modelValue', { ...localMapping })
}
</script>

<style scoped>
.pm-editor { display: flex; flex-direction: column; gap: 12px; }
.pm-row { display: flex; flex-direction: column; gap: 4px; }
.pm-label { font-size: 12px; font-weight: 600; color: #334155; }
.pm-type { font-weight: 400; color: #94a3b8; }
.pm-source { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.pm-select { max-width: 100px; flex-shrink: 0; }
.pm-empty { font-size: 12px; color: #94a3b8; text-align: center; padding: 8px; }
</style>
