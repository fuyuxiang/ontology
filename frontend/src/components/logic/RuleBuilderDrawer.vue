<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ruleApi } from '../../api/rules'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'
import ConditionBuilder from './ConditionBuilder.vue'
import type { EntityListItem, EntityAttribute } from '../../types'

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
const entityAttrsCache = ref<Record<string, EntityAttribute[]>>({})
const entityNameCache = ref<Record<string, string>>({})
const relatedEntityIds = ref<string[]>([])
const saving = ref(false)

const form = ref({
  name: '',
  description: '',
  entity_id: '',
  priority: 'medium' as 'high' | 'medium' | 'low',
  tags: '',
  conditions_json: [] as any[],
})

function normalizeAttrType(type: string): string {
  if (type === 'enum') return 'string'
  if (type === 'computed' || type === 'json' || type === 'ref') return 'string'
  return type
}

const attributeGroups = computed(() => {
  const mainId = form.value.entity_id
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

watch(() => form.value.entity_id, async (id) => {
  if (id) {
    await loadEntityAttributes(id)
    await loadRelatedEntities(id)
  } else {
    relatedEntityIds.value = []
  }
})

async function load() {
  entities.value = await entityApi.list()
  if (props.lockedEntityId) form.value.entity_id = props.lockedEntityId
  if (form.value.entity_id) {
    await loadEntityAttributes(form.value.entity_id)
    await loadRelatedEntities(form.value.entity_id)
  }
  if (props.editId) {
    const rule = await ruleApi.detail(props.editId)
    form.value.name = rule.name
    form.value.description = (rule as any).description ?? ''
    form.value.entity_id = rule.entityId
    form.value.priority = rule.priority
    form.value.tags = Array.isArray((rule as any).tags) ? (rule as any).tags.join(', ') : ''
    const cj = (rule as any).conditions_json
    if (cj && cj.length) {
      form.value.conditions_json = cj.map((c: any) => ({
        ...c,
        source: c.source ?? c.field ?? '',
      }))
    }
    if (form.value.entity_id) {
      await loadEntityAttributes(form.value.entity_id)
      await loadRelatedEntities(form.value.entity_id)
    }
  }
}

function resetForm() {
  form.value = {
    name: '', description: '',
    entity_id: props.lockedEntityId ?? '',
    priority: 'medium',
    tags: '',
    conditions_json: [],
  }
  relatedEntityIds.value = []
}

watch(() => props.visible, (v) => {
  if (v) { resetForm(); load() }
})

onMounted(() => { if (props.visible) { resetForm(); load() } })

async function save() {
  if (!form.value.name.trim()) { toast.error('请填写规则名称'); return }
  if (!form.value.entity_id) { toast.error('请选择关联实体'); return }
  if (!form.value.conditions_json.length) { toast.error('请至少添加一条触发条件'); return }
  saving.value = true
  try {
    const conditions = form.value.conditions_json.map((c: any) => ({
      ...c,
      field: c.source,
    }))
    const payload: any = {
      name: form.value.name.trim(),
      description: form.value.description,
      entity_id: form.value.entity_id,
      priority: form.value.priority,
      tags: form.value.tags.split(',').map(t => t.trim()).filter(Boolean),
      conditions_json: conditions,
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
          <button class="btn-icon" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-panel__body">
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
              <div class="form-row-inline">
                <div class="form-row" style="flex:1;">
                  <label class="form-label">关联实体 *</label>
                  <select class="form-input" v-model="form.entity_id" :disabled="!!lockedEntityId">
                    <option value="" disabled>— 请选择实体 —</option>
                    <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
                  </select>
                </div>
                <div class="form-row" style="flex:1;">
                  <label class="form-label">优先级</label>
                  <div class="mode-switch" style="margin-bottom:0;">
                    <button
                      v-for="p in (['high','medium','low'] as const)" :key="p"
                      type="button"
                      :class="{ active: form.priority === p }"
                      @click="form.priority = p"
                    >{{ p === 'high' ? '高' : p === 'medium' ? '中' : '低' }}</button>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <label class="form-label">标签（逗号分隔）</label>
                <input class="form-input" v-model="form.tags" placeholder="例如：核心, 风控" />
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="form-section__title">触发条件</div>
            <div v-if="!form.entity_id" class="form-hint">请先选择关联实体，以加载可用属性</div>
            <ConditionBuilder
              v-else
              v-model="form.conditions_json"
              :entity-id="form.entity_id"
              :entity-attributes="[]"
              :available-functions="[]"
              :attribute-groups="attributeGroups"
            />
          </div>
        </div>

        <div class="drawer-panel__footer">
          <button class="btn-secondary" @click="emit('close')">取消</button>
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
