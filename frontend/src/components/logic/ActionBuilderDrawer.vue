<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { actionApi, type ActionTypeInfo } from '../../api/actions'
import { entityApi } from '../../api/ontology'
import AiCodePanel from './AiCodePanel.vue'
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

const entities = ref<EntityListItem[]>([])
const actionTypes = ref<ActionTypeInfo[]>([])
const saving = ref(false)
const testing = ref(false)
const testInput = ref('{}')
const testResult = ref<string | null>(null)
const testSuccess = ref<boolean | null>(null)
const savedId = ref<string | null>(null)
const showAiPanel = ref(false)
const tempSessionId = ref(crypto.randomUUID())

const aiTargetId = computed(() => savedId.value || props.editId || `tmp_${tempSessionId.value}`)

const form = ref({
  name: '',
  description: '',
  category: 'domain' as 'domain' | 'system',
  entity_id: '',
  action_type: '',
  status: 'active' as 'active' | 'inactive',
  parameters: [] as { name: string; type: string; required: boolean; description: string; entity_id?: string; attribute_id?: string }[],
})
const typeConfigValues = ref<Record<string, string>>({})

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
      id: a.id, name: a.name, name_cn: a.name_cn || a.name, data_type: a.data_type || 'string',
    }))
  } catch {
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
  if (attributeId && p.entity_id && entityAttributes.value[p.entity_id]) {
    const attr = entityAttributes.value[p.entity_id].find(a => a.id === attributeId)
    if (attr) {
      const typeMap: Record<string, string> = { integer: 'number', float: 'number', double: 'number', boolean: 'boolean', date: 'date', datetime: 'date' }
      p.type = typeMap[attr.data_type] ?? 'string'
    }
  }
}

function resetForm() {
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
    parameters: [],
  }
}

async function load() {
  entities.value = await entityApi.list()
  actionTypes.value = await actionApi.types()
  if (props.lockedEntityId) form.value.entity_id = props.lockedEntityId
  if (props.editId) {
    try {
      const action = await actionApi.detail(props.editId)
      savedId.value = action.id
      form.value.name = action.name
      form.value.description = action.description || ''
      form.value.category = action.category
      form.value.entity_id = action.entity_id || ''
      form.value.action_type = action.action_type
      form.value.status = action.status as 'active' | 'inactive'
      form.value.parameters = (action.parameters_json ?? []) as any
      if (action.type_config) {
        for (const [k, v] of Object.entries(action.type_config)) {
          typeConfigValues.value[k] = typeof v === 'object' ? JSON.stringify(v) : String(v)
        }
      }
      for (const p of form.value.parameters) {
        if (p.entity_id) loadAttributesForEntity(p.entity_id)
      }
    } catch (e) { console.warn('回填动作表单失败', e) }
  }
}

watch(() => props.visible, (v) => { if (v) { resetForm(); load() } })
onMounted(() => { if (props.visible) { resetForm(); load() } })

function addParam() {
  form.value.parameters.push({ name: '', type: 'string', required: false, description: '', entity_id: undefined, attribute_id: undefined })
}

function removeParam(idx: number) {
  form.value.parameters.splice(idx, 1)
}

async function save() {
  if (!form.value.name.trim()) { alert('请填写行动名称'); return }
  if (!form.value.action_type) { alert('请选择行动类型'); return }
  if (form.value.category === 'domain' && !form.value.entity_id) { alert('领域行动需选择关联实体'); return }

  saving.value = true
  try {
    const typeConfig: Record<string, any> = {}
    for (const [key, val] of Object.entries(typeConfigValues.value)) {
      if (!val) continue
      const schema = currentConfigSchema.value[key]
      if (schema?.type === 'object') {
        try { typeConfig[key] = JSON.parse(val) } catch { typeConfig[key] = val }
      } else {
        typeConfig[key] = val
      }
    }

    const payload: any = {
      name: form.value.name.trim(),
      description: form.value.description || undefined,
      category: form.value.category,
      action_type: form.value.action_type,
      type_config: Object.keys(typeConfig).length > 0 ? typeConfig : undefined,
      parameters_json: form.value.parameters.length > 0 ? form.value.parameters : undefined,
    }
    if (form.value.category === 'domain') {
      payload.entity_id = form.value.entity_id
    }

    let result: any
    if (props.editId) {
      result = await actionApi.update(props.editId, payload)
    } else {
      result = await actionApi.create(payload)
    }
    savedId.value = result.id

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
  if (!savedId.value && !props.editId) {
    alert('请先保存行动后再测试')
    return
  }
  testing.value = true
  testResult.value = null
  testSuccess.value = null
  try {
    let params: Record<string, any> = {}
    try { params = JSON.parse(testInput.value) } catch { alert('输入参数不是合法 JSON'); testing.value = false; return }
    const id = (props.editId ?? savedId.value)!
    const res = await actionApi.execute(id, params)
    testSuccess.value = res?.success === true
    testResult.value = JSON.stringify(res, null, 2)
  } catch (e: any) {
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
      <div class="drawer-panel">
        <div class="drawer-panel__header">
          <h2>{{ editId ? '编辑行动' : '新建行动' }}</h2>
          <button class="btn-sm-edit" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-panel__body">
          <div class="form-section">
            <div class="form-section__title">基本信息</div>
            <div class="rule-form">
              <div class="form-row">
                <label class="form-label">行动名称 *</label>
                <input class="form-input" v-model="form.name" placeholder="行动名称" />
              </div>
              <div class="form-row">
                <label class="form-label">描述</label>
                <textarea class="form-input" v-model="form.description" rows="2" placeholder="行动用途描述" />
              </div>
              <div class="form-row-inline">
                <div class="form-row" style="flex:1;">
                  <label class="form-label">分类 *</label>
                  <select class="form-input" v-model="form.category">
                    <option value="domain">领域行动（绑定实体）</option>
                    <option value="system">系统行动（不绑定实体）</option>
                  </select>
                </div>
                <div v-if="form.category === 'domain'" class="form-row" style="flex:1;">
                  <label class="form-label">关联实体 *</label>
                  <select class="form-input" v-model="form.entity_id" :disabled="!!lockedEntityId">
                    <option value="" disabled>选择实体</option>
                    <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="form-section__title">行动类型</div>
            <div class="rule-form">
              <div class="form-row">
                <label class="form-label">类型 *</label>
                <select class="form-input" v-model="form.action_type">
                  <option value="" disabled>选择类型</option>
                  <option v-for="t in actionTypes" :key="t.type_key" :value="t.type_key">{{ t.label }} - {{ t.description }}</option>
                </select>
              </div>
              <template v-if="form.action_type && Object.keys(currentConfigSchema).length > 0">
                <p class="text-caption" style="margin-bottom:8px;">配置「{{ getTypeLabel(form.action_type) }}」的参数：</p>
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
            <div class="form-section__title">输入参数</div>
            <div v-for="(p, idx) in form.parameters" :key="idx" class="condition-row" style="flex-wrap:wrap;gap:6px;">
              <input class="form-input" style="flex:1.5;min-width:80px;" v-model="p.name" placeholder="参数名" />
              <select class="form-input" style="flex:1;min-width:80px;" v-model="p.type">
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="boolean">boolean</option>
                <option value="date">date</option>
                <option value="json">json</option>
              </select>
              <input class="form-input" style="flex:2;min-width:100px;" v-model="p.description" placeholder="说明" />
              <select class="form-input" style="flex:1.2;min-width:90px;" :value="p.entity_id || ''" @change="onParamEntityChange(p, ($event.target as HTMLSelectElement).value)">
                <option value="">— 关联实体 —</option>
                <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
              </select>
              <select class="form-input" style="flex:1.5;min-width:100px;" :value="p.attribute_id || ''" @change="onParamAttributeChange(p, ($event.target as HTMLSelectElement).value)" :disabled="!p.entity_id">
                <option value="">— 关联属性 —</option>
                <option v-for="a in (entityAttributes[p.entity_id || ''] || [])" :key="a.id" :value="a.id">{{ a.name_cn || a.name }}</option>
              </select>
              <label style="display:flex;align-items:center;gap:4px;font-size:12px;flex-shrink:0;">
                <input type="checkbox" v-model="p.required" /> 必填
              </label>
              <button class="btn-sm-del" @click="removeParam(idx)">✕</button>
            </div>
            <button class="btn-sm-exec" style="margin-top:4px;" @click="addParam">+ 添加参数</button>
          </div>

          <div v-if="form.action_type === 'custom_script'" class="form-section">
            <div class="form-section__title">逻辑体</div>
            <div class="logic-toolbar" style="margin-bottom:8px;">
              <button type="button" class="btn-secondary" @click="showAiPanel = true">AI 生成</button>
            </div>
            <textarea class="form-input form-input--code" v-model="typeConfigValues['script']" rows="8" placeholder="def run(params):&#10;    return ..." />
          </div>

          <div class="form-section">
            <div class="form-section__title">测试面板</div>
            <div class="form-row">
              <label class="form-label">输入参数（JSON）</label>
              <textarea class="form-input form-input--code" v-model="testInput" rows="3" placeholder='{"param1": "value1"}' />
            </div>
            <button class="btn-sm-exec" :disabled="testing" style="margin-top:8px;" @click="runTest">
              {{ testing ? '执行中…' : '▶ 运行测试' }}
            </button>
            <div v-if="testResult !== null" style="margin-top:12px;padding:10px 12px;border-radius:6px;font-size:12px;font-family:monospace;white-space:pre-wrap;"
              :style="testSuccess ? 'background:#f0fdf4;border:1px solid #86efac;' : 'background:#fef2f2;border:1px solid #fca5a5;'">
              {{ testResult }}
            </div>
          </div>
        </div>

        <div class="drawer-panel__footer">
          <button class="btn-sm-edit" @click="emit('close')">取消</button>
          <button class="btn-primary" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存' }}
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
      :context-entity-ids="form.entity_id ? [form.entity_id] : []"
      @close="showAiPanel = false"
      @apply="(code: string) => { typeConfigValues['script'] = code; showAiPanel = false }"
    />
  </Teleport>
</template>

<style scoped>
@import '../../views/logic/logic-shared.css';
</style>
