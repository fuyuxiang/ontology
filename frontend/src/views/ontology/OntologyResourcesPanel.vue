<template>
  <section class="resource-panel">
    <header><h2>{{ labels[kind] }}</h2><button :disabled="loading || saving" @click="load">刷新</button></header>
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <p v-if="loading" role="status">加载中…</p>
    <template v-else>
      <form v-if="canEdit && kind === 'groups'" @submit.prevent="saveGroup">
        <label>分组名称 <input v-model="groupName" required maxlength="120" /></label>
        <fieldset><legend>当前本体对象</legend><label v-for="entity in entities" :key="entity.id"><input v-model="groupEntities" type="checkbox" :value="entity.id" />{{ entity.name_cn || entity.name }}</label></fieldset>
        <button :disabled="saving || !groupName.trim()">{{ editId ? '保存修改' : '创建分组' }}</button><button type="button" @click="resetForm">取消</button>
      </form>
      <form v-if="canEdit && kind === 'shared-attrs'" @submit.prevent="saveAttribute">
        <label>英文名 <input v-model="attribute.name" required maxlength="100" /></label><label>中文名 <input v-model="attribute.name_cn" /></label>
        <label>类型 <select v-model="attribute.data_type"><option v-for="type in ['string','number','boolean','date','enum']" :key="type">{{ type }}</option></select></label>
        <label>说明 <input v-model="attribute.description" /></label><button :disabled="saving || !attribute.name.trim()">{{ editId ? '保存修改' : '创建共享属性' }}</button><button type="button" @click="resetForm">取消</button>
      </form>
      <p v-if="!rows.length && !error">暂无{{ labels[kind] }}</p>
      <template v-if="kind === 'api'"><div v-for="group in rows" :key="group.entity" class="resource-card"><h3>{{ group.entityCn || group.entity }}</h3><div v-for="endpoint in group.endpoints" :key="endpoint.path + endpoint.method"><code>{{ endpoint.method }} {{ endpoint.path }}</code><p>{{ endpoint.description }}</p></div></div></template>
      <template v-else><div v-for="row in rows" :key="row.id" class="resource-card">
        <template v-if="kind === 'groups'"><h3>{{ row.name }}</h3><p>{{ (row.entity_ids || []).map((id: string) => entities.find(entity => entity.id === id)?.name_cn || id).join('、') || '无成员' }}</p><button @click="editGroup(row)" :disabled="!canEdit">编辑</button><button :disabled="!canDelete || saving" @click="remove(row.id)">删除</button></template>
        <template v-else-if="kind === 'shared-attrs'"><h3>{{ row.name_cn || row.name }} <code>{{ row.name }}</code></h3><p>{{ row.data_type }} · {{ row.description }}</p><button @click="editAttribute(row)" :disabled="!canEdit">编辑</button><button :disabled="!canDelete || saving" @click="remove(row.id)">删除</button></template>
        <template v-else-if="kind === 'history'"><h3>v{{ row.version_number }} {{ row.name }}</h3><p>{{ row.status }} · {{ row.is_active ? '活动版本' : '历史版本' }} · {{ formatPlatformDateTime(row.created_at) }}</p><button @click="router.push({ path: '/ontology/publish', query: { ontology_id: ontologyId, version_id: row.id } })">查看与治理</button></template>
        <template v-else><h3>{{ row.action_name || row.action_id }} <small>{{ row.source }}</small></h3><p>状态：{{ row.status }} · {{ formatPlatformDateTime(row.created_at) }} · ID：{{ row.id }}</p><p v-if="row.error" role="alert">{{ row.error }}</p><details><summary>输入与结果</summary><pre>{{ JSON.stringify({ params: row.params, result: row.result }, null, 2) }}</pre></details></template>
      </div></template>
    </template>
  </section>
</template>
<script setup lang="ts">
import { formatPlatformDateTime } from '../../utils/platformTime'
import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit, canDelete } = useManagementPermission('entity:write')
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { get, post, put, del } from '../../api/client'
const props = defineProps<{ ontologyId: string; kind: 'groups' | 'tasks' | 'history' | 'api' | 'shared-attrs'; entities: any[] }>()
const router = useRouter()
const labels = { groups: '对象分组', tasks: '操作任务记录', history: '版本历史', api: '接口定义', 'shared-attrs': '共享属性' }
const rows = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const editId = ref<string | null>(null)
const groupName = ref('')
const groupEntities = ref<string[]>([])
const attribute = ref({ name: '', name_cn: '', data_type: 'string', description: '' })
let request = 0
const resourcePath = computed(() => props.kind === 'shared-attrs' ? '/shared-attributes' : `/ontology/${props.ontologyId}/groups`)
function resetForm() { editId.value = null; groupName.value = ''; groupEntities.value = []; attribute.value = { name: '', name_cn: '', data_type: 'string', description: '' } }
async function load() {
  const current = ++request
  const ontologyId = props.ontologyId
  loading.value = true; error.value = ''; rows.value = []
  try {
    let result: any
    if (props.kind === 'groups' || props.kind === 'tasks') result = await get(`/ontology/${ontologyId}/${props.kind}`)
    else if (props.kind === 'shared-attrs') result = await get('/shared-attributes', { params: { ontology_id: ontologyId } })
    else if (props.kind === 'history') result = await get<any[]>('/ontology-publish/versions', {params:{ontology_id:ontologyId}})
    else result = (await get<any>('/ontology-api/endpoints', { params: { ontology_id: ontologyId } })).groups
    if (current === request && ontologyId === props.ontologyId) rows.value = Array.isArray(result) ? result : result.items || []
  } catch (exception: any) { if (current === request) error.value = exception?.response?.data?.detail || exception.message || '加载失败' }
  finally { if (current === request) loading.value = false }
}
function editGroup(row: any) { editId.value = row.id; groupName.value = row.name; groupEntities.value = [...row.entity_ids] }
function editAttribute(row: any) { editId.value = row.id; attribute.value = { name: row.name, name_cn: row.name_cn || '', data_type: row.data_type, description: row.description || '' } }
async function save(payload: any) {
  if (!canEdit.value || saving.value) return
  saving.value = true
  try { if (editId.value) await put(`${resourcePath.value}/${editId.value}`, payload); else await post(resourcePath.value, payload); resetForm(); await load(); message.success('保存成功') }
  catch (exception: any) { message.error(exception?.response?.data?.detail || '保存失败') }
  finally { saving.value = false }
}
function saveGroup() { return save({ name: groupName.value.trim(), entity_ids: groupEntities.value }) }
function saveAttribute() { return save({ ...attribute.value, name: attribute.value.name.trim(), ontology_id: props.ontologyId }) }
async function remove(id: string) {
  if (!canDelete.value || saving.value || !window.confirm('确定删除该记录？')) return
  saving.value = true
  try { await del(`${resourcePath.value}/${id}`); await load(); message.success('删除成功') }
  catch (exception: any) { message.error(exception?.response?.data?.detail || '删除失败') }
  finally { saving.value = false }
}
watch(() => [props.ontologyId, props.kind], () => { resetForm(); void load() }, { immediate: true })
</script>
<style scoped>
.resource-panel { padding: 24px; min-width: 0; }.resource-panel header { display: flex; justify-content: space-between; gap: 12px; align-items: center; }.resource-panel h2 { font-size: 18px; }.resource-panel form { display: flex; flex-wrap: wrap; gap: 12px; padding: 16px; border: 1px solid #ddd; margin-bottom: 16px; }.resource-panel label { display: inline-flex; gap: 8px; align-items: center; }.resource-panel fieldset { flex-basis: 100%; display: flex; flex-wrap: wrap; gap: 12px; }.resource-panel input,.resource-panel select { max-width: 100%; padding: 6px; }.resource-panel button { padding: 6px 12px; cursor: pointer; }.resource-card { border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin: 12px 0; overflow-wrap: anywhere; }.resource-card h3 { margin: 0 0 8px; font-size: 15px; }.resource-card pre { white-space: pre-wrap; overflow-wrap: anywhere; }.resource-card button { margin-right: 8px; }
</style>
