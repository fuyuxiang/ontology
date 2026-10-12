<template>
  <div class="attr-panel">
    <div class="attr-panel__header"><button class="attr-panel__back" @click="emit('back')">返回对象列表</button><strong>{{ entity.name }}</strong><span>{{ entity.name_cn }}</span></div>
    <div v-if="loading" role="status">加载中…</div>
    <div v-else-if="error" role="alert"><p>{{ error }}</p><button @click="loadDetail">重新加载</button></div>
    <template v-else>
      <p v-if="entity.is_shared">该对象由其他本体共享；定义修改请进入所属本体。</p>
      <div class="entity-editor"><label>英文名 <a-input v-model:value="metadata.name" :disabled="!editable" /></label><label>中文名 <a-input v-model:value="metadata.name_cn" :disabled="!editable" /></label><label>层级 <a-select v-model:value="metadata.tier" :disabled="!editable" :options="[{value:1,label:'L1'},{value:2,label:'L2'},{value:3,label:'L3'}]" /></label><label>说明 <a-textarea v-model:value="metadata.description" :disabled="!editable" /></label><a-button :disabled="!editable" :loading="saving" @click="saveMetadata">保存对象定义</a-button></div>
      <div class="attr-panel__header"><strong>属性 ({{ attrs.length }})</strong><a-button :disabled="!editable" @click="editAttribute()">新增属性</a-button></div>
      <div class="attr-panel__grid"><div v-for="attr in attrs" :key="attr.id" class="attr-card"><div class="attr-card__head"><code>{{ attr.name }}</code><span>{{ attr.type }}</span></div><p>{{ attr.description }}</p><p>{{ attr.required ? '必填' : '可选' }}{{ attr.shared_attribute_id ? ' · 共享属性引用' : '' }}</p><a-button size="small" :disabled="!editable" @click="editAttribute(attr)">编辑</a-button> <a-button size="small" danger :disabled="!editable || !canDelete" @click="removeAttribute(attr)">删除</a-button></div></div>
      <p v-if="!attrs.length">暂无属性</p>
      <div v-if="pendingActionSpecs.length">
        <strong>导入的待配置动作建议</strong><p>这些建议缺少执行器配置，尚未注册为可执行动作。请在 <router-link to="/logic/actions">行动页面</router-link> 选择类型、目标对象并填写实际配置。</p>
        <pre>{{ JSON.stringify(pendingActionSpecs, null, 2) }}</pre>
      </div>
      <div class="attr-panel__header instance-header"><strong>已发布版本的真实业务实例</strong><a-button :loading="querying" @click="queryInstances(true)">查询 / 刷新</a-button></div>
      <p>使用当前活动发布版本的字段和绑定；定义编辑请重新发布后查看。过滤条件为 JSON 对象。</p>
      <a-input v-model:value="filters" placeholder='{"id":"DEV-001"}' @press-enter="queryInstances(true)" />
      <p v-if="queryError" role="alert">{{ queryError }}</p><div v-if="queried && !querying && !queryError" class="instance-data"><pre>{{ JSON.stringify(instances, null, 2) }}</pre><a-button :disabled="offset === 0" @click="changePage(-1)">上一页</a-button> <span>第 {{ offset / 20 + 1 }} 页</span> <a-button :disabled="instances.length < 20" @click="changePage(1)">下一页</a-button></div>
    </template>
    <a-modal v-model:open="attributeOpen" :title="attributeId ? '编辑属性' : '新增属性'" :confirm-loading="attributeSaving" @ok="saveAttribute">
      <div class="entity-editor"><label>共享属性引用 <a-select v-model:value="attribute.shared_attribute_id" allow-clear :options="sharedAttributes.map(item => ({value:item.id,label:item.name}))" @change="selectShared" /></label><label>属性名 <a-input v-model:value="attribute.name" /></label><label>类型 <a-select v-model:value="attribute.type" :options="types.map(type => ({value:type,label:type}))" :disabled="!!attribute.shared_attribute_id" /></label><label><a-checkbox v-model:checked="attribute.required">必填</a-checkbox></label><label>说明 <a-textarea v-model:value="attribute.description" /></label></div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { entityApi } from '../../api/ontology'
import { get, post } from '../../api/client'
import { useManagementPermission } from '../../composables/useManagementPermission'
import type { EntityListItem, EntityAttribute, EntityCreateAttribute, Tier } from '../../types'
const props = defineProps<{ entity: EntityListItem }>()
const emit = defineEmits<{ back: []; changed: [] }>()
const { canEdit, canDelete } = useManagementPermission('entity:write')
const editable = computed(() => canEdit.value && !props.entity.is_shared)
const loading = ref(false), saving = ref(false), error = ref('')
const attrs = ref<EntityAttribute[]>([])
const pendingActionSpecs = ref<Array<Record<string, unknown>>>([])
const metadata = ref({ name: '', name_cn: '', tier: 2 as Tier, description: '' })
const sharedAttributes = ref<any[]>([])
let detailRequest = 0
function failure(exception: any) { const value = exception?.response?.data?.detail; return typeof value === 'string' ? value : value?.message || exception.message || '请求失败' }
async function loadDetail() {
  const request = ++detailRequest, entityId = props.entity.id
  loading.value = true; error.value = ''; attrs.value = []; pendingActionSpecs.value = []; resetQuery()
  try { const detail = await entityApi.detail(entityId); if (request !== detailRequest) return; attrs.value = detail.attributes; pendingActionSpecs.value = Array.isArray(detail.config_json?.pending_action_specs) ? detail.config_json.pending_action_specs as Array<Record<string, unknown>> : []; metadata.value = { name: detail.name, name_cn: detail.name_cn, tier: detail.tier, description: detail.description || '' }; if (detail.ontology_id) sharedAttributes.value = await get<any[]>('/shared-attributes', { params: { ontology_id: detail.ontology_id } }) }
  catch (exception) { if (request === detailRequest) error.value = failure(exception) }
  finally { if (request === detailRequest) loading.value = false }
}
async function saveMetadata() { if (!editable.value || saving.value) return; if (!metadata.value.name.trim() || !metadata.value.name_cn.trim()) { message.error('请填写对象名称'); return } saving.value = true; try { await entityApi.update(props.entity.id, metadata.value); message.success('对象定义已保存；已发布版本保持原内容'); emit('changed') } catch (exception) { message.error(failure(exception)) } finally { saving.value = false } }
const types = ['string','number','boolean','date','enum','ref','json','computed']
const emptyAttribute = (): EntityCreateAttribute => ({ name:'', type:'string', required:false, description:'', shared_attribute_id:null })
const attributeOpen = ref(false), attributeSaving = ref(false), attributeId = ref<string | null>(null), attribute = ref<EntityCreateAttribute>(emptyAttribute())
function editAttribute(current?: EntityAttribute) { attributeId.value = current?.id || null; attribute.value = current ? { name:current.name, type:current.type, required:current.required, description:current.description, shared_attribute_id:current.shared_attribute_id || null } : emptyAttribute(); attributeOpen.value = true }
function selectShared(id: string | undefined) { if (!id) { attribute.value.shared_attribute_id = null; return } const shared = sharedAttributes.value.find(item => item.id === id); if (shared) attribute.value.type = shared.data_type }
async function saveAttribute() { if (!editable.value || attributeSaving.value) return; if (!attribute.value.name.trim()) { message.error('请填写属性名'); return } attributeSaving.value = true; try { if (attributeId.value) await entityApi.updateAttribute(props.entity.id, attributeId.value, attribute.value); else await entityApi.createAttribute(props.entity.id, attribute.value); attributeOpen.value = false; await loadDetail(); emit('changed'); message.success('属性已保存') } catch (exception) { message.error(failure(exception)) } finally { attributeSaving.value = false } }
async function removeAttribute(current: EntityAttribute) { if (!editable.value || !canDelete.value || !confirm(`删除属性 ${current.name}？`)) return; try { await entityApi.deleteAttribute(props.entity.id, current.id); await loadDetail(); emit('changed'); message.success('属性已删除') } catch (exception) { message.error(failure(exception)) } }
const instances = ref<any[]>([]), filters = ref('{}'), offset = ref(0), queried = ref(false), querying = ref(false), queryError = ref('')
let queryRequest = 0
function resetQuery() { ++queryRequest; instances.value = []; filters.value = '{}'; offset.value = 0; queried.value = false; querying.value = false; queryError.value = '' }
async function queryInstances(reset = false) { if (reset) offset.value = 0; const request = ++queryRequest, entityId = props.entity.id; querying.value = true; queried.value = true; queryError.value = ''; try { const parsed = JSON.parse(filters.value || '{}'); if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('过滤条件必须为 JSON 对象'); const result = await post<{ instances:any[] }>('/ontology-api/query', { entity_name:entityId, filters:parsed, limit:20, offset:offset.value }); if (request === queryRequest) instances.value = result.instances } catch (exception) { if (request === queryRequest) { instances.value = []; queryError.value = failure(exception) } } finally { if (request === queryRequest) querying.value = false } }
function changePage(direction: number) { offset.value = Math.max(0, offset.value + direction * 20); void queryInstances() }
onMounted(loadDetail)
watch(() => props.entity.id, () => { attributeOpen.value = false; void loadDetail() })
</script>
<style scoped>
.attr-panel { padding: 0; }

.attr-panel__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.attr-panel__back {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.attr-panel__back:hover { background: var(--neutral-50, #fafafa); }

.attr-panel__info {
  display: flex;
  flex-wrap: wrap;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.attr-panel__name {
  overflow-wrap: anywhere;
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
}

.attr-panel__name-cn {
  font-size: 13px;
  color: var(--neutral-500, #888);
}

.attr-panel__tier {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.attr-panel__tier--1 { background: #eff6ff; color: #2563eb; }
.attr-panel__tier--2 { background: #f0fdf4; color: #16a34a; }
.attr-panel__tier--3 { background: #fefce8; color: #ca8a04; }

.attr-panel__loading {
  padding: 40px 0;
  text-align: center;
  color: var(--neutral-400, #aaa);
  font-size: 13px;
}

.attr-panel__count {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-600, #666);
  margin-bottom: 12px;
}

.attr-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 12px;
}

.attr-card {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.15s;
}

.attr-card:hover { border-color: var(--neutral-200, #e5e5e5); }

.attr-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.attr-card__name {
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-800, #222);
}

.attr-card__type {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--neutral-100, #f0f0f0);
  color: var(--neutral-600, #666);
}

.attr-card__type--string { background: #eff6ff; color: #2563eb; }
.attr-card__type--number { background: #f0fdf4; color: #16a34a; }
.attr-card__type--boolean { background: #fefce8; color: #ca8a04; }
.attr-card__type--date { background: #fdf4ff; color: #a855f7; }
.attr-card__type--ref { background: #fff7ed; color: #ea580c; }
.attr-card__type--enum { background: #f5f3ff; color: #7c3aed; }
.attr-card__type--json { background: #f0fdfa; color: #0d9488; }
.attr-card__type--computed { background: #fef2f2; color: #dc2626; }

.attr-card__required {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #16a34a;
  margin-bottom: 4px;
}

.attr-card__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}

.attr-card__desc {
  overflow-wrap: anywhere;
  font-size: 12px;
  color: var(--neutral-500, #888);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.attr-panel__empty {
  padding: 60px 0;
  text-align: center;
  color: var(--neutral-400, #aaa);
  font-size: 13px;
}
.attr-panel__empty .attr-panel__back { margin: 12px auto 0; }
.entity-editor { display:grid; gap:12px; margin-bottom:24px; } .entity-editor label { display:grid; gap:6px; } .instance-header { margin-top:28px; } .instance-data { overflow:auto; max-height:480px; }
</style>
