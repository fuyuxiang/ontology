<script setup lang="ts">
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()

import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('rule:write')
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { actionApi, type ActionTypeInfo } from '../../api/actions'
import { entityApi } from '../../api/ontology'
import AiCodePanel from './AiCodePanel.vue'
import { useOntologyStore } from '../../store/ontology'
import { randomUUID } from '../../utils/uuid'
import type { EntityListItem } from '../../types'

const props = defineProps<{
  visible: boolean
  editId?: string
  lockedEntityId?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', val: { id: string; name: string }): void
}>()

const route = useRoute()
const router = useRouter()
const ontologyStore = useOntologyStore()
const targetOntologyId = ref<string | null>(ontologyStore.currentOntologyId || null)

const entities = ref<EntityListItem[]>([])
const actionTypes = ref<ActionTypeInfo[]>([])
const loading = ref(false), loadError = ref('')
let loadRequest = 0
const saving = ref(false)
const testing = ref(false)
const testInput = ref('{}')
const testResult = ref<string | null>(null)
const testSuccess = ref<boolean | null>(null)
const savedId = ref<string | null>(null)
const savedSignature = ref('')
let testRequest = 0
const showAiPanel = ref(false)
const tempSessionId = ref(randomUUID())

const aiTargetId = computed(() => savedId.value || props.editId || `tmp_${tempSessionId.value}`)

const form = ref({
  name: '',
  description: '',
  category: 'domain' as 'domain' | 'system',
  entity_id: '',
  action_type: '',
  status: 'active' as 'active' | 'inactive' | 'draft',
  output_schema_json: '[]',
  parameters: [] as { name: string; type: string; required: boolean; description: string; entity_id?: string; attribute_id?: string; entity_attribute_id?: string; default_value?: string | null; use_default?: boolean }[],
})
const typeConfigValues = ref<Record<string, string>>({})
const currentSignature = computed(() => JSON.stringify({form:form.value, config:typeConfigValues.value}))
const hasUnsavedChanges = computed(() => !savedSignature.value || savedSignature.value !== currentSignature.value)
watch([form, typeConfigValues, testInput], () => { ++testRequest; testResult.value = null; testSuccess.value = null }, {deep:true, flush:'sync'})


const entityAttributes = ref<Record<string, { id: string; name: string; name_cn: string; data_type: string }[]>>({})

const currentConfigSchema = computed(() => {
  const t = actionTypes.value.find(at => at.type_key === form.value.action_type)
  return t?.config_schema || {}
})

function getTypeLabel(typeKey: string): string {
  const t = actionTypes.value.find(at => at.type_key === typeKey)
  return t?.label || typeKey
}

async function loadAttributesForEntity(entityId: string) {
  if (!entityId || entityAttributes.value[entityId]) return
  try {
    const entity = await entityApi.detail(entityId)
    entityAttributes.value[entityId] = (entity.attributes ?? []).map((a: any) => ({
      id: a.id, name: a.name, name_cn: a.name_cn || a.name, data_type: a.type || a.data_type || 'string',
    }))
  } catch {
    loadError.value = text('关联对象属性加载失败，请重新打开编辑器重试')
    entityAttributes.value[entityId] = []
  }
}

function onParamEntityChange(p: any, entityId: string) {
  p.entity_id = entityId || undefined
  p.attribute_id = undefined
  p.entity_attribute_id = undefined
  if (entityId) loadAttributesForEntity(entityId)
}

function onParamAttributeChange(p: any, attributeId: string) {
  p.attribute_id = attributeId || undefined
  p.entity_attribute_id = attributeId || undefined
  if (attributeId && p.entity_id && entityAttributes.value[p.entity_id]) {
    const attr = entityAttributes.value[p.entity_id].find(a => a.id === attributeId)
    if (attr) {
      const typeMap: Record<string, string> = { number: 'number', json: 'object', integer: 'number', float: 'number', double: 'number', boolean: 'boolean', date: 'date', datetime: 'date' }
      p.type = typeMap[attr.data_type] ?? 'string'
    }
  }
}

function resetForm() {
  targetOntologyId.value = ontologyStore.currentOntologyId || null
  ++testRequest; savedSignature.value = ''
  savedId.value = null
  testResult.value = null
  testSuccess.value = null
  typeConfigValues.value = {}
  form.value = {
    name: '',
    description: '',
    category: 'domain',
    entity_id: props.lockedEntityId ?? '',
    action_type: '',
    status: 'active',
    output_schema_json: '[]',
    parameters: [],
  }
}

async function load() {
  const request = ++loadRequest, editId = props.editId, target = ontologyStore.currentOntologyId
  loading.value = true; loadError.value = ''
  try {
  const availableEntities = await entityApi.list({ ontology_id: target || undefined })
  if (request !== loadRequest || !props.visible || props.editId !== editId || ontologyStore.currentOntologyId !== target) return
  entities.value = availableEntities
  actionTypes.value = await actionApi.types()
  if (props.lockedEntityId) form.value.entity_id = props.lockedEntityId
  if (props.editId) {
    try {
      const action = await actionApi.detail(props.editId)
      if (request !== loadRequest || !props.visible || props.editId !== editId) return
      targetOntologyId.value = action.ontology_id || null
      if (targetOntologyId.value !== target) {
        entities.value = await entityApi.list({ontology_id:targetOntologyId.value || undefined})
        if (request !== loadRequest || !props.visible || props.editId !== editId) return
      }
      savedId.value = action.id
      form.value.name = action.name
      form.value.description = action.description || ''
      form.value.category = action.category
      form.value.entity_id = action.entity_id || ''
      form.value.action_type = action.action_type
      form.value.status = action.status as 'active' | 'inactive' | 'draft'
      form.value.parameters = (action.parameters_json ?? []).map(p => ({...p, attribute_id:p.entity_attribute_id, use_default:p.default_value !== null && p.default_value !== undefined})) as any
      form.value.output_schema_json = JSON.stringify(action.output_schema || [], null, 2)
      if (form.value.parameters.some(p => p.entity_attribute_id)) {
        await Promise.all(entities.value.map(entity => loadAttributesForEntity(entity.id)))
        if (request !== loadRequest || !props.visible || props.editId !== editId) return
        for (const p of form.value.parameters) {
          const owner = entities.value.find(entity => entityAttributes.value[entity.id]?.some(attr => attr.id === p.entity_attribute_id))
          if (owner) p.entity_id = owner.id
        }
      }
      if (action.type_config) {
        for (const [k, v] of Object.entries(action.type_config)) {
          typeConfigValues.value[k] = typeof v === 'object' ? JSON.stringify(v) : String(v)
        }
      }
      savedSignature.value = currentSignature.value
      for (const p of form.value.parameters) {
        if (p.entity_id) loadAttributesForEntity(p.entity_id)
      }
    } catch (e: any) { loadError.value = e?.response?.data?.detail || e.message || '动作加载失败' }
  }
  } catch (e: any) { if (request === loadRequest) loadError.value = e?.response?.data?.detail || e.message || '编辑器加载失败' } finally { if (request === loadRequest) loading.value = false }
}

watch([() => props.visible, () => props.editId, () => ontologyStore.currentOntologyId], ([v]) => { ++loadRequest; if (v) { resetForm(); void load() } })
onMounted(() => { if (props.visible) { resetForm(); load() } })

function addParam() {
  form.value.parameters.push({ name: '', type: 'string', required: false, description: '', entity_id: undefined, attribute_id: undefined })
}

function removeParam(idx: number) {
  form.value.parameters.splice(idx, 1)
}

async function save() {
  if (!canEdit.value || saving.value || loading.value || loadError.value) return
  if (!form.value.name.trim()) { alert(text('请填写行动名称')); return }
  if (!form.value.action_type) { alert(text('请选择行动类型')); return }
  if (form.value.category === 'domain' && !form.value.entity_id) { alert(text('领域行动需选择关联实体')); return }

  saving.value = true
  const signature = currentSignature.value
  try {
    let outputSchema: any
    try {
      outputSchema = JSON.parse(form.value.output_schema_json)
      if (!Array.isArray(outputSchema) || outputSchema.some(field => !field || typeof field.name !== 'string' || !field.name.trim() || typeof field.type !== 'string' || !field.type.trim())) throw new Error()
      if (new Set(outputSchema.map(field => field.name)).size !== outputSchema.length) throw new Error()
    } catch { throw new Error(text('输出结构必须为字段名不重复的 JSON 数组，每个字段包含 name/type')) }
    for (const [key, schema] of Object.entries(currentConfigSchema.value) as [string, any][]) {
      if (form.value.status !== 'draft' && schema.required && !typeConfigValues.value[key]?.trim()) {
        if (key === 'script' && typeConfigValues.value.source_path) continue
        throw new Error(`请填写行动配置：${key}`)
      }
    }
    const typeConfig: Record<string, any> = {}
    for (const [key, val] of Object.entries(typeConfigValues.value)) {
      if (!val) continue
      const schema = currentConfigSchema.value[key]
      if (schema?.type === 'object') {
        try { typeConfig[key] = JSON.parse(val); if (!typeConfig[key] || Array.isArray(typeConfig[key]) || typeof typeConfig[key] !== 'object') throw new Error() } catch { throw new Error(`${key} 必须为有效 JSON 对象`) }
      } else {
        typeConfig[key] = val
      }
    }

    const payload: any = {
      name: form.value.name.trim(),
      description: form.value.description,
      category: form.value.category,
      action_type: form.value.action_type,
      type_config: typeConfig,
      parameters_json: form.value.parameters.map(({entity_id: _entity, attribute_id, use_default, ...parameter}) => ({...parameter, entity_attribute_id:attribute_id || parameter.entity_attribute_id || null, default_value:use_default ? parameter.default_value ?? '' : null})),
      output_schema: outputSchema,
      status: form.value.status,
      ontology_id: targetOntologyId.value,
    }
    payload.entity_id = form.value.category === 'domain' ? form.value.entity_id : null

    let result: any
    if (props.editId) {
      result = await actionApi.update(props.editId, payload)
    } else {
      result = await actionApi.create(payload)
    }
    savedId.value = result.id
    savedSignature.value = signature

    if (!props.editId && route.query.from === 'builder') {
      const sid = route.query.session_id as string
      const oid = route.query.object_id as string
      if (sid && oid && result?.id) {
        router.push({ path: '/builder', query: { session_id: sid, attach_to: oid, new_id: result.id, kind: 'action' } })
        return
      }
    }

    emit('saved', { id: result.id, name: result.name })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '保存失败'
    alert(`保存行动失败: ${msg}`)
  } finally {
    saving.value = false
  }
}

async function runTest() {
  if (testing.value || saving.value || loading.value || loadError.value) return
  if (hasUnsavedChanges.value) { alert(text('当前内容尚未保存，请保存后重新验证')); return }
  if (!savedId.value && !props.editId) {
    alert(text('请先保存行动后再测试'))
    return
  }
  const request = ++testRequest, signature = currentSignature.value, target = props.editId
  testing.value = true
  testResult.value = null
  testSuccess.value = null
  try {
    let params: Record<string, any> = {}
    try { params = JSON.parse(testInput.value) } catch { alert(text('输入参数不是合法 JSON')); testing.value = false; return }
    const id = (props.editId ?? savedId.value)!
    const res = await actionApi.execute(id, params, true)
    if (request !== testRequest || signature !== currentSignature.value || !props.visible || target !== props.editId) return
    testSuccess.value = res?.success === true
    testResult.value = JSON.stringify(res, null, 2)
  } catch (e: any) {
    if (request !== testRequest || !props.visible || target !== props.editId) return
    testSuccess.value = false
    testResult.value = e?.message ?? '执行失败'
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <Transition name="drawer">
    <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
      <p v-if="loading" role="status">{{ text("编辑器加载中…") }}</p><p v-if="loadError" role="alert">{{ loadError }}</p>
      <div class="drawer-panel">
        <div class="drawer-panel__header">
          <h2>{{ editId ? text('编辑行动') : text('新建行动') }}</h2>
          <button class="btn-sm-edit" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-panel__body">
          <div class="form-section">
            <div class="form-section__title">{{ text("基本信息") }}</div>
            <div class="rule-form">
              <div class="form-row">
                <label class="form-label">{{ text("行动名称 *") }}</label>
                <input class="form-input" v-model="form.name" :placeholder="text('行动名称')" />
              </div>
              <div class="form-row">
                <label class="form-label">{{ text("描述") }}</label>
                <textarea class="form-input" v-model="form.description" rows="2" :placeholder="text('行动用途描述')" />
              </div>
              <div class="form-row"><label class="form-label">{{ text("状态") }}</label><select class="form-input" v-model="form.status"><option value="draft">{{ text("草稿") }}</option><option value="active">{{ text("激活") }}</option><option value="inactive">{{ text("停用") }}</option></select></div>
              <div class="form-row-inline">
                <div class="form-row" style="flex:1;">
                  <label class="form-label">{{ text("分类 *") }}</label>
                  <select class="form-input" v-model="form.category">
                    <option value="domain">{{ text("领域行动（绑定实体）") }}</option>
                    <option value="system">{{ text("系统行动（不绑定实体）") }}</option>
                  </select>
                </div>
                <div v-if="form.category === 'domain'" class="form-row" style="flex:1;">
                  <label class="form-label">{{ text("关联实体 *") }}</label>
                  <select class="form-input" v-model="form.entity_id" :disabled="!!lockedEntityId">
                    <option value="" disabled>{{ text("选择实体") }}</option>
                    <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="form-section__title">{{ text("行动类型") }}</div>
            <div class="rule-form">
              <div class="form-row">
                <label class="form-label">{{ text("类型 *") }}</label>
                <select class="form-input" v-model="form.action_type">
                  <option value="" disabled>{{ text("选择类型") }}</option>
                  <option v-for="t in actionTypes" :key="t.type_key" :value="t.type_key">{{ t.label }} - {{ t.description }}</option>
                </select>
              </div>
              <template v-if="form.action_type && Object.keys(currentConfigSchema).length > 0">
                <p class="text-caption" style="margin-bottom:8px;">配置「{{ getTypeLabel(form.action_type) }}」的参数：</p>
                <p v-if="form.action_type==='modify_attribute'" class="text-caption">{{ text("赋值输入可使用参数名（例如 status）、固定值（例如 maintenance），或显式表达式（例如 expr: params['temperature'] / 100）；$status 是固定文字。先模拟预览并核对解析后的值，再到列表确认执行。") }}</p>
                <div v-for="(field, key) in currentConfigSchema" :key="key" class="form-row">
                  <label class="form-label">{{ field.description || key }}</label>
                  <textarea v-if="field.type === 'object' || key === 'script' || key === 'sql'" v-model="typeConfigValues[key as string]" class="form-input form-input--code" rows="3" />
                  <select v-else-if="field.enum" v-model="typeConfigValues[key as string]" class="form-input">
                    <option v-for="opt in field.enum" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                  <input v-else v-model="typeConfigValues[key as string]" class="form-input" :required="field.required" />
                </div>
              </template>
            </div>
          </div>

          <div class="form-section">
            <div class="form-section__title">{{ text("输入参数") }}</div>
            <div v-for="(p, idx) in form.parameters" :key="idx" class="condition-row" style="flex-wrap:wrap;gap:6px;">
              <input class="form-input" style="flex:1.5;min-width:80px;" v-model="p.name" :placeholder="text('参数名')" />
              <select class="form-input" style="flex:1;min-width:80px;" v-model="p.type">
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="integer">integer</option><option value="float">float</option>
                <option value="object">object</option><option value="array">array</option>
                <option value="datetime">datetime</option>
                <option value="boolean">boolean</option>
                <option value="date">date</option>
                <option value="json">json</option>
              </select>
              <input class="form-input" style="flex:2;min-width:100px;" v-model="p.description" :placeholder="text('说明')" />
              <select class="form-input" style="flex:1.2;min-width:90px;" :value="p.entity_id || ''" @change="onParamEntityChange(p, ($event.target as HTMLSelectElement).value)">
                <option value="">{{ text("— 关联实体 —") }}</option>
                <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
              </select>
              <select class="form-input" style="flex:1.5;min-width:100px;" :value="p.attribute_id || ''" @change="onParamAttributeChange(p, ($event.target as HTMLSelectElement).value)" :disabled="!p.entity_id">
                <option value="">{{ text("— 关联属性 —") }}</option>
                <option v-for="a in (entityAttributes[p.entity_id || ''] || [])" :key="a.id" :value="a.id">{{ a.name_cn || a.name }}</option>
              </select>
              <label style="display:flex;align-items:center;gap:4px;font-size:12px;flex-shrink:0;">
                <input type="checkbox" v-model="p.required" /> {{ text("必填") }}
              </label>
              <label style="display:flex;align-items:center;gap:4px;font-size:12px;"><input type="checkbox" v-model="p.use_default" /> {{ text("默认值") }}</label>
              <input v-if="p.use_default" class="form-input" style="flex:1.5;min-width:100px;" v-model="p.default_value" :placeholder="text('字符串原文；数值/对象/布尔使用JSON')" />
              <button class="btn-sm-del" @click="removeParam(idx)">✕</button>
            </div>
            <button class="btn-sm-exec" style="margin-top:4px;" @click="addParam">{{ text("+ 添加参数") }}</button>
          </div>

          <div class="form-section">
            <div class="form-section__title">{{ text("输出结构（JSON 数组）") }}</div>
            <textarea class="form-input form-input--code" v-model="form.output_schema_json" rows="3" placeholder='[{"name":"risk","type":"number","description":"风险值"}]' />
          </div>

          <div v-if="form.action_type === 'custom_script'" class="form-section">
            <div class="form-section__title">{{ text("逻辑体") }}</div>
            <div class="logic-toolbar" style="margin-bottom:8px;">
              <button type="button" class="btn-secondary" @click="showAiPanel = true">{{ text("AI 生成") }}</button>
            </div>
            <textarea class="form-input form-input--code" v-model="typeConfigValues['script']" rows="8" placeholder="result = {&quot;risk&quot;: params[&quot;temperature&quot;] / 100}" />
          </div>

          <div class="form-section">
            <div class="form-section__title">{{ text("模拟预览 · 校验配置与参数；业务副作用请在行动列表确认执行") }}</div>
            <div class="form-row">
              <label class="form-label">{{ text("输入参数（JSON）") }}</label>
              <textarea class="form-input form-input--code" v-model="testInput" rows="3" placeholder='{"param1": "value1"}' />
            </div>
            <button class="btn-sm-exec" :disabled="testing || saving || loading || !!loadError || hasUnsavedChanges" style="margin-top:8px;" @click="runTest">
              {{ testing ? text('预览中…') : text('▶ 模拟预览') }}
            </button>
            <p v-if="hasUnsavedChanges" class="text-caption">{{ text("当前内容尚未保存，保存后才能验证。") }}</p>
            <div v-if="testResult !== null" style="margin-top:12px;padding:10px 12px;border-radius:6px;font-size:12px;font-family:monospace;white-space:pre-wrap;"
              :style="testSuccess ? 'background:#f0fdf4;border:1px solid #86efac;' : 'background:#fef2f2;border:1px solid #fca5a5;'">
              {{ testResult }}
            </div>
          </div>
        </div>

        <div class="drawer-panel__footer">
          <button class="btn-sm-edit" @click="emit('close')">{{ text("取消") }}</button>
          <button class="btn-primary" :disabled="!canEdit || saving || loading || !!loadError" @click="save">
            {{ saving ? text('保存中…') : text('保存') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
  <Teleport to="body">
    <AiCodePanel
      :visible="showAiPanel"
      :target-type="'action'"
      :target-id="aiTargetId"
      :ontology-id="targetOntologyId"
      :execution-mode="'custom_script'"
      :context-entity-ids="form.entity_id ? [form.entity_id] : []"
      @close="showAiPanel = false"
      @apply="(code: string) => { typeConfigValues['script'] = code; showAiPanel = false }"
    />
  </Teleport>
</template>

<style scoped>
@import '../../views/logic/logic-shared.css';
</style>
