<template>
  <ModalDialog :visible="visible" title="新建业务规则" width="560px" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="rule-form">
      <div class="form-row">
        <label class="form-label">规则名称</label>
        <input v-model="form.name" class="form-input" placeholder="如 高价值客户识别" required />
      </div>
      <div class="form-row">
        <label class="form-label">关联实体</label>
        <select v-model="form.entity_id" class="form-input" required>
          <option value="" disabled>选择实体...</option>
          <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }} ({{ e.name_cn }})</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-label">触发条件</label>
        <!-- TODO(attribute_id binding): when this form is upgraded to structured conditions
             (conditions_json list), each condition row should include entity_id + attribute_id
             selectors so the field reference can be linked to a specific ontology entity attribute.
             See FunctionBuilderDrawer.vue input_params rows for the implemented pattern. -->
        <input v-model="form.condition_expr" class="form-input form-input--code" placeholder="如 arpu >= 100 AND tenure >= 12" required />
      </div>
      <div class="form-row">
        <label class="form-label">执行动作</label>
        <input v-model="form.action_desc" class="form-input" placeholder="如 标记为高价值客户" required />
      </div>
      <div class="form-row-inline">
        <div class="form-row" style="flex:1">
          <label class="form-label">优先级</label>
          <select v-model="form.priority" class="form-input">
            <option value="high">高</option>
            <option value="medium">中</option>
            <option value="low">低</option>
          </select>
        </div>
        <div class="form-row" style="flex:1">
          <label class="form-label">状态</label>
          <select v-model="form.status" class="form-input">
            <option value="active">活跃</option>
            <option value="warning">警告</option>
            <option value="disabled">禁用</option>
          </select>
        </div>
      </div>
    </form>

    <template #footer>
      <button class="btn-secondary" @click="$emit('close')">取消</button>
      <button class="btn-primary" @click="handleSubmit" :disabled="submitting">
        {{ submitting ? '创建中...' : '创建规则' }}
      </button>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, watch } from 'vue'
import ModalDialog from './ModalDialog.vue'
import { ruleApi } from '../../api/rules'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'

const props = defineProps<{
  visible: boolean
  prefillName?: string
  prefillCondition?: string
  prefillAction?: string
  prefillEntityId?: string
}>()
const emit = defineEmits<{ close: []; created: [rule: { id: string; name: string }] }>()
const toast = useToast()

const submitting = ref(false)
const entities = ref<{ id: string; name: string; name_cn: string }[]>([])

const form = reactive({
  name: '',
  entity_id: '',
  condition_expr: '',
  action_desc: '',
  priority: 'medium',
  status: 'active',
})

function applyPrefill() {
  if (props.prefillName) form.name = props.prefillName
  if (props.prefillCondition) form.condition_expr = props.prefillCondition
  if (props.prefillAction) form.action_desc = props.prefillAction
  if (props.prefillEntityId) form.entity_id = props.prefillEntityId
}

onMounted(async () => {
  applyPrefill()
  try {
    const list = await entityApi.list()
    entities.value = list.map(e => ({
      id: e.id, name: e.name, name_cn: e.name_cn,
    }))
  } catch { /* ignore */ }
})

watch(() => props.visible, (v) => { if (v) applyPrefill() })

async function handleSubmit() {
  if (!form.name || !form.entity_id || !form.condition_expr || !form.action_desc) return
  submitting.value = true
  try {
    const rule = await ruleApi.create(form as never)
    toast.success('规则创建成功')
    form.name = ''
    form.entity_id = ''
    form.condition_expr = ''
    form.action_desc = ''
    form.priority = 'medium'
    form.status = 'active'
    emit('created', { id: (rule as any).id, name: (rule as any).name })
    emit('close')
  } catch (e) {
    toast.error(`创建失败: ${(e as Error).message}`)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.rule-form { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row-inline { display: flex; gap: 12px; }
.form-label { font-size: var(--text-code-size); font-weight: 500; color: var(--neutral-600); }
.form-input {
  padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); outline: none;
}
.form-input:focus { border-color: var(--semantic-500); }
.form-input--code { font-family: var(--font-mono); font-size: var(--text-code-size); }
.btn-primary {
  padding: 8px 20px; border-radius: var(--radius-md); border: none;
  background: var(--semantic-600); color: var(--neutral-0); font-size: var(--text-body-size); font-weight: 500; cursor: pointer;
}
.btn-primary:hover { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary {
  padding: 8px 16px; border-radius: var(--radius-md); border: 1px solid var(--neutral-300);
  background: var(--neutral-0); color: var(--neutral-700); font-size: var(--text-body-size); cursor: pointer;
}
.btn-secondary:hover { background: var(--neutral-50); }
</style>
