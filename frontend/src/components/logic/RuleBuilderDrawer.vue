<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ruleApi } from '../../api/rules'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'
import ConditionBuilder from './ConditionBuilder.vue'
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

const entities = ref<EntityListItem[]>([])
const saving = ref(false)

const form = ref({
  name: '',
  description: '',
  entity_id: '',
  priority: 'medium' as 'high' | 'medium' | 'low',
  tags: '',
  condition_mode: 'structured' as 'structured' | 'expression',
  conditions_json: [] as any[],
  condition_expression: '',
  action_id: '',
  action_desc: '',
  input_params: [] as { name: string; type: string; required: boolean }[],
})

async function load() {
  entities.value = await entityApi.list()
  if (props.lockedEntityId) form.value.entity_id = props.lockedEntityId
  if (props.editId) {
    const rule = await ruleApi.detail(props.editId)
    form.value.name = rule.name
    form.value.description = (rule as any).description ?? ''
    form.value.entity_id = rule.entityId
    form.value.priority = rule.priority
    form.value.tags = Array.isArray((rule as any).tags) ? (rule as any).tags.join(', ') : ''
    form.value.condition_expression = rule.condition ?? ''
    form.value.action_id = (rule as any).action_id ?? ''
    form.value.action_desc = (rule as any).action_desc ?? ''
    form.value.input_params = (rule as any).input_params ?? []
    const cj = (rule as any).conditions_json
    if (cj && cj.length) {
      form.value.condition_mode = 'structured'
      form.value.conditions_json = cj
    } else {
      form.value.condition_mode = 'expression'
    }
  }
}

function resetForm() {
  form.value = {
    name: '', description: '',
    entity_id: props.lockedEntityId ?? '',
    priority: 'medium',
    tags: '',
    condition_mode: 'structured',
    conditions_json: [],
    condition_expression: '',
    action_id: '', action_desc: '',
    input_params: [],
  }
}

watch(() => props.visible, (v) => {
  if (v) { resetForm(); load() }
})

onMounted(() => { if (props.visible) { resetForm(); load() } })

function addParam() {
  form.value.input_params.push({ name: '', type: 'string', required: false })
}
function removeParam(idx: number) {
  form.value.input_params.splice(idx, 1)
}

async function save() {
  if (!form.value.name.trim()) { toast.error('请填写规则名称'); return }
  saving.value = true
  try {
    const payload: any = {
      name: form.value.name.trim(),
      description: form.value.description,
      entity_id: form.value.entity_id || null,
      priority: form.value.priority,
      tags: form.value.tags.split(',').map(t => t.trim()).filter(Boolean),
      action_id: form.value.action_id || null,
      action_desc: form.value.action_desc,
      input_params: form.value.input_params,
    }
    if (form.value.condition_mode === 'structured') {
      payload.conditions_json = form.value.conditions_json
    } else {
      payload.condition = form.value.condition_expression
    }
    let result: any
    if (props.editId) {
      result = await ruleApi.update(props.editId, payload)
    } else {
      result = await ruleApi.create(payload)
    }
    toast.success(props.editId ? '规则已更新' : '规则已创建')
    emit('saved', { id: result.id, name: result.name })
  } catch (e: any) {
    toast.error(e?.message ?? '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Transition name="drawer">
    <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
      <div class="drawer-panel">
        <div class="drawer-panel__header">
          <h2>{{ editId ? '编辑规则' : '新建规则' }}</h2>
          <button class="btn-sm-edit" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-panel__body">
          <!-- Basic info -->
          <div class="form-section">
            <div class="form-section__title">基本信息</div>
            <div class="rule-form">
              <div class="form-row">
                <label class="form-label">规则名称 *</label>
                <input class="form-input" v-model="form.name" placeholder="请输入规则名称" />
              </div>
              <div class="form-row">
                <label class="form-label">描述</label>
                <textarea class="form-input" v-model="form.description" rows="2" placeholder="规则描述（可选）" />
              </div>
              <div class="form-row">
                <label class="form-label">关联实体</label>
                <select class="form-input" v-model="form.entity_id" :disabled="!!lockedEntityId">
                  <option value="">— 不绑定实体 —</option>
                  <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
                </select>
              </div>
              <div class="form-row">
                <label class="form-label">优先级</label>
                <div style="display:flex;gap:16px;align-items:center;margin-top:4px;">
                  <label v-for="p in ['high','medium','low']" :key="p" style="display:flex;align-items:center;gap:4px;font-size:13px;cursor:pointer;">
                    <input type="radio" :value="p" v-model="form.priority" />
                    {{ p === 'high' ? '高' : p === 'medium' ? '中' : '低' }}
                  </label>
                </div>
              </div>
              <div class="form-row">
                <label class="form-label">标签（逗号分隔）</label>
                <input class="form-input" v-model="form.tags" placeholder="例如：核心, 风控" />
              </div>
            </div>
          </div>

          <!-- Trigger conditions -->
          <div class="form-section">
            <div class="form-section__title">触发条件</div>
            <div class="mode-switch">
              <button :class="{ active: form.condition_mode === 'structured' }" @click="form.condition_mode = 'structured'">结构化</button>
              <button :class="{ active: form.condition_mode === 'expression' }" @click="form.condition_mode = 'expression'">表达式</button>
            </div>
            <ConditionBuilder
              v-if="form.condition_mode === 'structured'"
              v-model="form.conditions_json"
              :entity-id="form.entity_id"
              :entity-attributes="[]"
              :available-functions="[]"
            />
            <textarea
              v-else
              class="form-input form-input--code"
              v-model="form.condition_expression"
              rows="4"
              placeholder="例如：entity.age > 18 AND entity.status == 'active'"
            />
          </div>

          <!-- Action reference -->
          <div class="form-section">
            <div class="form-section__title">动作引用</div>
            <div class="rule-form">
              <div class="form-row">
                <label class="form-label">动作 ID</label>
                <input class="form-input" v-model="form.action_id" placeholder="action_id（可选）" />
              </div>
              <div class="form-row">
                <label class="form-label">动作说明</label>
                <input class="form-input" v-model="form.action_desc" placeholder="简述触发后执行的动作" />
              </div>
            </div>
          </div>

          <!-- Input params -->
          <div class="form-section">
            <div class="form-section__title">输入参数</div>
            <div v-for="(p, idx) in form.input_params" :key="idx" class="condition-row">
              <input class="form-input" style="flex:2;" v-model="p.name" placeholder="参数名" />
              <select class="form-input" style="flex:1.5;" v-model="p.type">
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="boolean">boolean</option>
                <option value="date">date</option>
                <option value="json">json</option>
              </select>
              <label style="display:flex;align-items:center;gap:4px;font-size:12px;flex-shrink:0;">
                <input type="checkbox" v-model="p.required" /> 必填
              </label>
              <button class="btn-sm-del" @click="removeParam(idx)">✕</button>
            </div>
            <button class="btn-sm-exec" style="margin-top:4px;" @click="addParam">+ 添加参数</button>
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
</template>

<style scoped>
@import '../../views/logic/logic-shared.css';
</style>
