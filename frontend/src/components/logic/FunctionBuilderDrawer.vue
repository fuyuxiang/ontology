<script setup lang="ts">
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()

import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('rule:write')
import { ref, watch, onMounted, computed } from 'vue'
import { functionApi } from '../../api/functions'
import AiCodePanel from './AiCodePanel.vue'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'
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

const toast = useToast()
const ontologyStore = useOntologyStore()
const targetOntologyId = ref<string | null>(ontologyStore.currentOntologyId || null)
const entities = ref<EntityListItem[]>([])
const loading = ref(false), loadError = ref('')
let loadRequest = 0
const saving = ref(false)
const testing = ref(false)
const testInput = ref('{}')
const testResult = ref<string | null>(null)
const testSuccess = ref<boolean | null>(null)
const testSimulated = ref(false)
const savedId = ref<string | null>(null)
const savedSignature = ref('')
let testRequest = 0
const tempSessionId = ref(randomUUID())
const showAiPanel = ref(false)

const aiTargetId = computed(() => savedId.value || props.editId || `tmp_${tempSessionId.value}`)

function onAiApply(code: string) {
  form.value.logic_body = code
  showAiPanel.value = false
}

const form = ref({
  name: '',
  callable_name: '',
  description: '',
  entity_id: '',
  entity_ids: [] as string[],
  return_type: 'string',
  tags: '',
  input_params: [] as { name: string; type: string; required: boolean; description: string; entity_id?: string; attribute_id?: string }[],
  logic_type: 'expression' as 'expression' | 'sql' | 'python',
  logic_body: '',
})


const currentSignature = computed(() => JSON.stringify(form.value))
const hasUnsavedChanges = computed(() => !savedSignature.value || savedSignature.value !== currentSignature.value)
watch([form, testInput], () => { ++testRequest; testResult.value = null; testSuccess.value = null; testSimulated.value = false }, {deep:true, flush:'sync'})
async function load() {
  const request = ++loadRequest, editId = props.editId, target = ontologyStore.currentOntologyId
  loading.value = true; loadError.value = ''
  try {
  const availableEntities = await entityApi.list({ ontology_id: target || undefined })
  if (request !== loadRequest || !props.visible || props.editId !== editId || ontologyStore.currentOntologyId !== target) return
  entities.value = availableEntities
  if (props.lockedEntityId) form.value.entity_ids = [props.lockedEntityId]
  if (props.editId) {
    const fn = await functionApi.detail(props.editId)
    if (request !== loadRequest || !props.visible || props.editId !== editId) return
    targetOntologyId.value = fn.ontology_id || null
    if (targetOntologyId.value !== target) {
      entities.value = await entityApi.list({ontology_id:targetOntologyId.value || undefined})
      if (request !== loadRequest || !props.visible || props.editId !== editId) return
    }
    savedId.value = fn.id
    form.value.name = fn.name
    form.value.callable_name = fn.callable_name
    form.value.description = fn.description
    form.value.entity_id = fn.entity_id ?? ''
    form.value.entity_ids = fn.entity_ids ?? (fn.entity_id ? [fn.entity_id] : [])
    form.value.return_type = fn.return_type
    form.value.tags = Array.isArray(fn.tags) ? fn.tags.join(', ') : ''
    form.value.input_params = (fn.input_schema ?? []) as any
    // pre-load attributes for any params that already have entity_id
    for (const p of form.value.input_params) {
      if ((p as any).entity_id) loadAttributesForEntity((p as any).entity_id)
    }
    form.value.logic_type = (fn.logic_type as any) ?? 'expression'
    form.value.logic_body = fn.logic_body ?? ''
    savedSignature.value = currentSignature.value
  }
  } catch (e: any) { if (request === loadRequest) loadError.value = e?.response?.data?.detail || e.message || '编辑器加载失败' } finally { if (request === loadRequest) loading.value = false }
}

function resetForm() {
  targetOntologyId.value = ontologyStore.currentOntologyId || null
  ++testRequest; savedSignature.value = ''
  savedId.value = null
  tempSessionId.value = randomUUID()
  testResult.value = null
  testSuccess.value = null
  form.value = {
    name: '', callable_name: '', description: '',
    entity_id: props.lockedEntityId ?? '',
    entity_ids: props.lockedEntityId ? [props.lockedEntityId] : [],
    return_type: 'string',
    tags: '',
    input_params: [],
    logic_type: 'expression',
    logic_body: '',
  }
}

// attribute_id binding: keyed by entity_id -> list of attributes
const entityAttributes = ref<Record<string, { id: string; name: string; name_cn: string; data_type: string }[]>>({})

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
  if (entityId) loadAttributesForEntity(entityId)
}

function onParamAttributeChange(p: any, attributeId: string) {
  p.attribute_id = attributeId || undefined
  // auto-fill type from attribute data_type when available
  if (attributeId && p.entity_id && entityAttributes.value[p.entity_id]) {
    const attr = entityAttributes.value[p.entity_id].find(a => a.id === attributeId)
    if (attr) {
      const typeMap: Record<string, string> = { number: 'number', json: 'object', integer: 'number', float: 'number', double: 'number', boolean: 'boolean', date: 'date', datetime: 'date' }
      p.type = typeMap[attr.data_type] ?? 'string'
    }
  }
}

watch([() => props.visible, () => props.editId, () => ontologyStore.currentOntologyId], ([v]) => { ++loadRequest; if (v) { resetForm(); void load() } })
onMounted(() => { if (props.visible) { resetForm(); load() } })

function addParam() {
  form.value.input_params.push({ name: '', type: 'string', required: false, description: '', entity_id: undefined, attribute_id: undefined })
}
function removeParam(idx: number) {
  form.value.input_params.splice(idx, 1)
}

async function save() {
  if (!canEdit.value || saving.value || loading.value || loadError.value) return
  if (!form.value.name.trim()) { toast.error(text('请填写函数名称')); return }
  if (!form.value.callable_name.trim()) { toast.error(text('请填写调用名称')); return }
  saving.value = true
  const signature = currentSignature.value
  try {
    const payload: any = {
      name: form.value.name.trim(),
      callable_name: form.value.callable_name.trim(),
      description: form.value.description,
      entity_id: form.value.entity_ids[0] || null,
      entity_ids: form.value.entity_ids,
      ontology_id: targetOntologyId.value,
      return_type: form.value.return_type,
      tags: form.value.tags.split(',').map(t => t.trim()).filter(Boolean),
      input_schema: form.value.input_params,
      logic_type: form.value.logic_type,
      logic_body: form.value.logic_body,
    }
    let result: any
    if (props.editId) {
      result = await functionApi.update(props.editId, payload)
    } else {
      result = await functionApi.create(payload)
    }
    savedId.value = result.id
    savedSignature.value = signature
    toast.success(props.editId ? '函数已更新' : '函数已创建')
    emit('saved', { id: result.id, name: result.name })
  } catch (e: any) {
    toast.error(e?.message ?? '保存失败')
  } finally {
    saving.value = false
  }
}

function fillTestTemplate() {
  // 根据已定义的输入参数生成 JSON 模板，按类型给默认占位值
  const tmpl: Record<string, any> = {}
  for (const p of form.value.input_params) {
    if (!p.name) continue
    const defaults: Record<string, any> = { number: 0, boolean: false, json: {}, date: new Date().toISOString().slice(0, 10), string: '' }
    tmpl[p.name] = defaults[p.type] ?? ''
  }
  testInput.value = JSON.stringify(tmpl, null, 2)
}

async function runTest() {
  if (testing.value || saving.value || loading.value || loadError.value) return
  if (hasUnsavedChanges.value) { toast.info(text('当前内容尚未保存，请保存后重新验证')); return }
  if (!savedId.value && !props.editId) {
    toast.info(text('请先保存函数后再测试'))
    return
  }
  const request = ++testRequest, signature = currentSignature.value, target = props.editId
  testing.value = true
  testResult.value = null
  testSuccess.value = null
  testSimulated.value = false
  try {
    let params: Record<string, any> = {}
    try { params = JSON.parse(testInput.value) } catch { toast.error(text('输入参数不是合法 JSON')); testing.value = false; return }
    const id = (props.editId ?? savedId.value)!
    const res = await functionApi.test(id, params)
    if (request !== testRequest || signature !== currentSignature.value || !props.visible || target !== props.editId) return
    testSimulated.value = res.simulated === true || res.outcome === 'simulated'
    testSuccess.value = res.success && !testSimulated.value
    testResult.value = testSimulated.value
      ? JSON.stringify(res.requested_write || { result: res.result }, null, 2)
      : res.success
      ? JSON.stringify(res.result, null, 2)
      : (res.error ?? '执行失败')
  } catch (e: any) {
    if (request !== testRequest || !props.visible || target !== props.editId) return
    testSuccess.value = false
    testResult.value = e?.message ?? '请求失败'
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
          <h2>{{ editId ? text('编辑函数') : text('新建函数') }}</h2>
          <button class="btn-sm-edit" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-panel__body">
          <!-- Basic info -->
          <div class="form-section">
            <div class="form-section__title">{{ text("基本信息") }}</div>
            <div class="rule-form">
              <div class="form-row-inline">
                <div class="form-row" style="flex:1;">
                  <label class="form-label">{{ text("函数名称 *") }}</label>
                  <input class="form-input" v-model="form.name" :placeholder="text('显示名称')" />
                </div>
                <div class="form-row" style="flex:1;">
                  <label class="form-label">{{ text("调用名称 *") }}</label>
                  <input class="form-input" v-model="form.callable_name" placeholder="snake_case" />
                </div>
              </div>
              <div class="form-row">
                <label class="form-label">{{ text("描述") }}</label>
                <textarea class="form-input" v-model="form.description" rows="2" :placeholder="text('函数用途描述')" />
              </div>
              <div class="form-row-inline">
                <div class="form-row" style="flex:1;">
                  <label class="form-label">{{ text("关联实体（可多选）") }}</label>
                  <select class="form-input" v-model="form.entity_ids" multiple :disabled="!!lockedEntityId" style="min-height: 80px;">
                    <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
                  </select>
                </div>
                <div class="form-row" style="flex:1;">
                  <label class="form-label">{{ text("返回类型") }}</label>
                  <select class="form-input" v-model="form.return_type">
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="date">date</option>
                    <option value="json">json</option>
                    <option value="array">array</option>
                  </select>
                </div>
              </div>
              <div class="form-row">
                <label class="form-label">{{ text("标签（逗号分隔）") }}</label>
                <input class="form-input" v-model="form.tags" :placeholder="text('例如：聚合, 计算')" />
              </div>
            </div>
          </div>

          <!-- Input params -->
          <div class="form-section">
            <div class="form-section__title">{{ text("输入参数") }}</div>
            <p class="text-caption" style="margin:-4px 0 8px;color:#888;font-size:12px;">
              {{ text("声明逻辑体需要的外部变量。在逻辑体中通过") }} <code>params['参数名']</code>{{ text("（SQL 用") }} <code>:参数名</code>{{ text("）引用；勾选「必填」后，执行时缺少该参数会直接报错。") }}
            </p>
            <div v-for="(p, idx) in form.input_params" :key="idx" class="condition-row" style="flex-wrap:wrap;gap:6px;">
              <input class="form-input" style="flex:1.5;min-width:80px;" v-model="p.name" :placeholder="text('参数名')" />
              <select class="form-input" style="flex:1;min-width:80px;" v-model="p.type">
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="boolean">boolean</option>
                <option value="date">date</option>
                <option value="json">json</option>
              </select>
              <input class="form-input" style="flex:2;min-width:100px;" v-model="p.description" :placeholder="text('说明（可选）')" />
              <!-- attribute_id binding: link this param to an ontology entity attribute for type-safety -->
              <select class="form-input" style="flex:1.2;min-width:90px;" :value="p.entity_id || ''" @change="onParamEntityChange(p, ($event.target as HTMLSelectElement).value)" :title="text('关联实体（可选）')">
                <option value="">{{ text("— 关联实体 —") }}</option>
                <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
              </select>
              <select class="form-input" style="flex:1.5;min-width:100px;" :value="p.attribute_id || ''" @change="onParamAttributeChange(p, ($event.target as HTMLSelectElement).value)" :disabled="!p.entity_id" :title="text('关联属性（可选）')">
                <option value="">{{ text("— 关联属性 —") }}</option>
                <option v-for="a in (entityAttributes[p.entity_id || ''] || [])" :key="a.id" :value="a.id">{{ a.name_cn || a.name }}</option>
              </select>
              <label style="display:flex;align-items:center;gap:4px;font-size:12px;flex-shrink:0;">
                <input type="checkbox" v-model="p.required" /> {{ text("必填") }}
              </label>
              <button class="btn-sm-del" @click="removeParam(idx)">✕</button>
            </div>
            <button class="btn-sm-exec" style="margin-top:4px;" @click="addParam">{{ text("+ 添加参数") }}</button>
          </div>

          <!-- Logic body -->
          <div class="form-section">
            <div class="form-section__title">{{ text("逻辑体") }}</div>
            <div class="mode-switch">
              <button :class="{ active: form.logic_type === 'expression' }" @click="form.logic_type = 'expression'">{{ text("表达式") }}</button>
              <button :class="{ active: form.logic_type === 'sql' }" @click="form.logic_type = 'sql'">SQL</button>
              <button :class="{ active: form.logic_type === 'python' }" @click="form.logic_type = 'python'">Python</button>
            </div>
            <div class="logic-toolbar" style="margin-bottom: 8px;">
              <button type="button" class="btn-secondary" @click="showAiPanel = true">
                {{ text("AI 生成") }}
              </button>
            </div>
            <textarea class="form-input form-input--code" v-model="form.logic_body" rows="8"
              :placeholder="form.logic_type === 'expression' ? `表达式，用 params['参数名'] 取输入参数\n例如：params['score'] * 0.8 + params['bonus']` : form.logic_type === 'sql' ? `SQL，用 :参数名 绑定输入参数\n例如：SELECT AVG(amount) FROM orders WHERE user_id = :user_id` : `Python，从 params 取参数，把结果赋给 result\n例如：\ndef calc(p):\n    return p['a'] + p['b']\nresult = calc(params)`" />
          </div>

          <!-- Test panel -->
          <div class="form-section">
            <div class="form-section__title">{{ text("测试面板") }}</div>
            <p class="text-caption" style="margin:-4px 0 8px;color:#888;font-size:12px;">
              {{ text("保存后可只读测试函数；写入请求将在首个写入处停止并显示预览，后续执行须由行动确认。JSON 的键应与参数名一致，作为") }} <code>params</code> {{ text("传入逻辑体。") }}
            </p>
            <div class="form-row">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <label class="form-label">{{ text("输入参数（JSON）") }}</label>
                <button type="button" class="btn-secondary" style="font-size:12px;padding:2px 8px;" @click="fillTestTemplate">{{ text("按定义生成") }}</button>
              </div>
              <textarea class="form-input form-input--code" v-model="testInput" rows="3" placeholder='{"参数名": "值"}' />
            </div>
            <button class="btn-sm-exec" :disabled="testing || saving || loading || !!loadError || hasUnsavedChanges" style="margin-top:8px;" @click="runTest">
              {{ testing ? text('执行中…') : text('▶ 运行测试') }}
            </button>
            <p v-if="hasUnsavedChanges" class="text-caption">{{ text("当前内容尚未保存，保存后才能验证。") }}</p>
            <div v-if="testResult !== null" style="margin-top:12px;padding:10px 12px;border-radius:6px;font-size:12px;font-family:monospace;white-space:pre-wrap;"
              :style="testSimulated ? 'background:#fffbeb;border:1px solid #fcd34d;' : testSuccess ? 'background:#f0fdf4;border:1px solid #86efac;' : 'background:#fef2f2;border:1px solid #fca5a5;'">
              <strong v-if="testSimulated">{{ text("写入模拟预览：未实际写入，函数在首个写入处停止。后续执行须由行动确认。") }}</strong>
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
      :target-type="'function'"
      :target-id="aiTargetId"
      :ontology-id="targetOntologyId"
      :execution-mode="form.logic_type"
      :context-entity-ids="form.entity_ids"
      @close="showAiPanel = false"
      @apply="onAiApply"
    />
  </Teleport>
</template>

<style scoped>
@import '../../views/logic/logic-shared.css';
</style>
