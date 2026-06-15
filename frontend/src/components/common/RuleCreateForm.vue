<template>
  <ModalDialog :visible="visible" title="新建业务规则" width="640px" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="rule-form">
      <div class="form-row">
        <label class="form-label">规则名称 *</label>
        <input v-model="form.name" class="form-input" placeholder="如 高价值客户识别" required />
      </div>
      <div class="form-row">
        <label class="form-label">关联实体 *</label>
        <select v-model="form.entity_id" class="form-input" required>
          <option value="" disabled>选择实体...</option>
          <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }} ({{ e.name_cn }})</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-label">触发条件 *</label>
        <div v-if="!form.entity_id" class="form-hint">请先选择关联实体</div>
        <ConditionBuilder
          v-else
          v-model="conditions"
          :entity-id="form.entity_id"
          :entity-attributes="[]"
          :available-functions="[]"
          :attribute-groups="attributeGroups"
        />
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
import { reactive, ref, computed, onMounted, watch } from 'vue'
import ModalDialog from './ModalDialog.vue'
import ConditionBuilder from '../logic/ConditionBuilder.vue'
import { ruleApi } from '../../api/rules'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'
import type { EntityAttribute } from '../../types'

const props = defineProps<{
  visible: boolean
  prefillName?: string
  prefillEntityId?: string
}>()
const emit = defineEmits<{ close: []; created: [rule: { id: string; name: string }] }>()
const toast = useToast()

const submitting = ref(false)
const entities = ref<{ id: string; name: string; name_cn: string }[]>([])
const entityAttrsCache = ref<Record<string, EntityAttribute[]>>({})
const entityNameCache = ref<Record<string, string>>({})
const relatedEntityIds = ref<string[]>([])
const conditions = ref<any[]>([])

const form = reactive({
  name: '',
  entity_id: '',
  priority: 'medium',
  status: 'active',
})

function normalizeAttrType(type: string): string {
  if (type === 'enum') return 'string'
  if (type === 'computed' || type === 'json' || type === 'ref') return 'string'
  return type
}

const attributeGroups = computed(() => {
  const mainId = form.entity_id
  if (!mainId) return []
  const groups: { entityName: string; entityLabel: string; attrs: { field: string; label: string; type: string }[] }[] = []
  const mainAttrs = entityAttrsCache.value[mainId]
  const mainName = entityNameCache.value[mainId] ?? ''
  if (mainAttrs?.length) {
    groups.push({
      entityName: mainName,
      entityLabel: `${mainName}（主实体）`,
      attrs: mainAttrs.map(a => ({
        field: `${mainName}.${a.name}`,
        label: a.description || a.name,
        type: normalizeAttrType(a.type),
      })),
    })
  }
  for (const relId of relatedEntityIds.value) {
    const relAttrs = entityAttrsCache.value[relId]
    const relName = entityNameCache.value[relId] ?? ''
    if (relAttrs?.length) {
      groups.push({
        entityName: relName,
        entityLabel: relName,
        attrs: relAttrs.map(a => ({
          field: `${relName}.${a.name}`,
          label: a.description || a.name,
          type: normalizeAttrType(a.type),
        })),
      })
    }
  }
  return groups
})

async function loadEntityAttributes(entityId: string) {
  if (!entityId || entityAttrsCache.value[entityId]) return
  try {
    const entity = await entityApi.detail(entityId)
    entityAttrsCache.value[entityId] = entity.attributes ?? []
    entityNameCache.value[entityId] = entity.name
  } catch { /* ignore */ }
}

async function loadRelatedEntities(entityId: string) {
  if (!entityId) { relatedEntityIds.value = []; return }
  try {
    const rels = await entityApi.relations(entityId)
    const ids = new Set<string>()
    for (const r of rels) {
      if (r.from_entity_id === entityId) ids.add(r.to_entity_id)
      else ids.add(r.from_entity_id)
    }
    relatedEntityIds.value = [...ids]
    await Promise.all(relatedEntityIds.value.map(id => loadEntityAttributes(id)))
  } catch {
    relatedEntityIds.value = []
  }
}

watch(() => form.entity_id, async (id) => {
  conditions.value = []
  if (id) {
    await loadEntityAttributes(id)
    await loadRelatedEntities(id)
  } else {
    relatedEntityIds.value = []
  }
})

function applyPrefill() {
  if (props.prefillName) form.name = props.prefillName
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
  if (form.entity_id) {
    await loadEntityAttributes(form.entity_id)
    await loadRelatedEntities(form.entity_id)
  }
})

watch(() => props.visible, (v) => { if (v) applyPrefill() })

async function handleSubmit() {
  if (!form.name || !form.entity_id) return
  if (!conditions.value.length) { toast.error('请至少添加一条触发条件'); return }
  submitting.value = true
  try {
    const conditionsJson = conditions.value.map((c: any) => ({
      ...c,
      field: c.source,
    }))
    const rule = await ruleApi.create({
      name: form.name,
      entity_id: form.entity_id,
      priority: form.priority,
      status: form.status,
      conditions_json: conditionsJson,
    } as never)
    toast.success('规则创建成功')
    form.name = ''
    form.entity_id = ''
    form.priority = 'medium'
    form.status = 'active'
    conditions.value = []
    relatedEntityIds.value = []
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
.form-hint { font-size: 12px; color: var(--neutral-500); padding: 8px 0; }
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
