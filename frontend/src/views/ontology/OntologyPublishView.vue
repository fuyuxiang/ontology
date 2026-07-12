<template>
  <div class="publish-page">
    <div class="publish-page__header">
      <div class="publish-page__title-row">
        <button v-if="selectedOntology" class="btn-back" @click="backToGrid">&larr; 返回</button>
        <h1 class="page-title">{{ selectedOntology ? selectedOntology.name : '本体发布环境' }}</h1>
      </div>
      <p class="page-desc">{{ selectedOntology ? `版本历史 · 共 ${selectedOntology.total_versions} 个版本` : '已发布本体一览，点击卡片查看版本历史' }}</p>
    </div>

    <!-- 第一级：本体卡片网格 -->
    <div v-if="!selectedOntology" class="card-grid">
      <div
        v-for="onto in ontologies"
        :key="onto.ontology_id"
        class="onto-card"
        @click="selectOntology(onto)"
      >
        <div class="onto-card__top">
          <div class="onto-card__icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </div>
          <div class="onto-card__info">
            <span class="onto-card__name">{{ onto.name }}</span>
            <span class="onto-card__code">{{ onto.code }}</span>
          </div>
          <span v-if="onto.active_version" class="onto-card__badge">v{{ onto.active_version.version_number }}</span>
        </div>
        <p class="onto-card__desc">{{ onto.description || '暂无描述' }}</p>
        <div class="onto-card__stats">
          <span>{{ onto.active_version?.entity_count || 0 }} 个实体</span>
          <span>{{ onto.total_versions }} 个版本</span>
        </div>
        <div class="onto-card__footer">
          <span class="onto-card__status">已发布</span>
          <span class="onto-card__time">{{ onto.active_version?.published_at ? formatTime(onto.active_version.published_at) : '—' }}</span>
        </div>
      </div>
      <div v-if="!ontologies.length && !loading" class="empty-state">
        <p>暂无已发布的本体</p>
        <p class="empty-state__hint">在本体详情页点击"发布"按钮即可发布本体</p>
      </div>
    </div>

    <!-- 第二级：版本历史详情 -->
    <div v-if="selectedOntology" class="publish-page__body">
      <div class="version-sidebar">
        <button class="btn-primary btn-block" @click="showCreateDialog = true">创建新版本</button>
        <div class="version-list">
          <div
            v-for="v in filteredVersions"
            :key="v.id"
            class="version-item"
            :class="{ 'version-item--active': selectedVersionId === v.id }"
            @click="selectVersion(v.id)"
          >
            <div class="version-item__badge" :class="`version-item__badge--${v.status}`">v{{ v.version_number }}</div>
            <div class="version-item__info">
              <span class="version-item__name">{{ v.name }}</span>
              <span class="version-item__meta">{{ v.entity_count }} 个实体 · {{ formatStatus(v.status) }}</span>
            </div>
            <span v-if="v.is_active" class="version-item__active">当前</span>
          </div>
          <div v-if="!filteredVersions.length" class="version-empty">暂无版本</div>
        </div>
      </div>

      <div class="version-main">
        <template v-if="detail">
          <div class="meta-card">
            <div class="meta-card__header">
              <h2>v{{ detail.version_number }} — {{ detail.name }}</h2>
              <span class="status-tag" :class="`status-tag--${detail.status}`">{{ formatStatus(detail.status) }}</span>
            </div>
            <p v-if="detail.description" class="meta-card__desc">{{ detail.description }}</p>
            <div class="meta-card__stats">
              <div class="res-stat"><span class="res-stat__value">{{ detail.entities.length }}</span><span class="res-stat__label">对象</span></div>
              <div class="res-stat"><span class="res-stat__value">{{ detail.relations.length }}</span><span class="res-stat__label">关系</span></div>
              <div class="res-stat"><span class="res-stat__value">{{ versionFunctions.length }}</span><span class="res-stat__label">逻辑</span></div>
              <div class="res-stat"><span class="res-stat__value">{{ versionActions.length }}</span><span class="res-stat__label">动作</span></div>
            </div>
            <div class="meta-card__timeline">
              <span v-if="detail.created_at">创建: {{ formatTime(detail.created_at) }}</span>
              <span v-if="detail.submitted_at">提交: {{ formatTime(detail.submitted_at) }}</span>
              <span v-if="detail.published_at">发布: {{ formatTime(detail.published_at) }}</span>
              <span v-if="detail.rejected_at">驳回: {{ formatTime(detail.rejected_at) }}</span>
            </div>
            <div v-if="detail.reject_reason" class="meta-card__reject">驳回原因: {{ detail.reject_reason }}</div>
          </div>

          <!-- 对象 -->
          <section class="res-section">
            <div class="res-section__header">
              <h3>对象<span class="res-section__count">{{ detail.entities.length }}</span></h3>
              <button v-if="detail.status === 'draft'" class="btn-link" @click="showEntitySelector = true">+ 添加实体</button>
            </div>
            <div v-if="detail.entities.length" class="res-grid">
              <div v-for="e in detail.entities" :key="e.id" class="res-card">
                <div class="res-card__top">
                  <span class="res-card__name">{{ e.name_cn }}</span>
                </div>
                <span class="res-card__en">{{ e.name }}</span>
                <p v-if="e.description" class="res-card__desc">{{ e.description }}</p>
                <div class="res-card__foot">
                  <span class="res-card__tag">属性 {{ e.mapped_count }}/{{ e.attribute_count }}</span>
                  <button v-if="detail.status === 'draft'" class="btn-link btn-link--danger" @click="removeEntity(e.source_entity_id)">移除</button>
                </div>
              </div>
            </div>
            <div v-else class="res-empty">暂无对象</div>
          </section>

          <!-- 关系 -->
          <section class="res-section">
            <div class="res-section__header"><h3>关系<span class="res-section__count">{{ detail.relations.length }}</span></h3></div>
            <div v-if="detail.relations.length" class="res-grid">
              <div v-for="r in detail.relations" :key="r.id" class="res-card">
                <div class="res-card__top">
                  <span class="res-card__name">{{ r.name || r.rel_type }}</span>
                  <span v-if="r.cardinality" class="res-card__tag res-card__tag--plain">{{ r.cardinality }}</span>
                </div>
                <span class="res-card__en">{{ r.rel_type }}</span>
                <div class="res-card__foot">
                  <span class="res-card__rel">{{ entityName(r.from_entity_id) }} → {{ entityName(r.to_entity_id) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="res-empty">暂无关系</div>
          </section>

          <!-- 逻辑 -->
          <section class="res-section">
            <div class="res-section__header"><h3>逻辑<span class="res-section__count">{{ versionFunctions.length }}</span></h3></div>
            <div v-if="versionFunctions.length" class="res-grid">
              <div v-for="f in versionFunctions" :key="f.id" class="res-card">
                <div class="res-card__top">
                  <span class="res-card__name">{{ f.name }}</span>
                  <span v-if="f.return_type" class="res-card__tag res-card__tag--plain">{{ f.return_type }}</span>
                </div>
                <span class="res-card__en">{{ entityName(f.version_entity_id) }}</span>
                <p v-if="f.description" class="res-card__desc">{{ f.description }}</p>
              </div>
            </div>
            <div v-else class="res-empty">暂无逻辑</div>
          </section>

          <!-- 动作 -->
          <section class="res-section">
            <div class="res-section__header"><h3>动作<span class="res-section__count">{{ versionActions.length }}</span></h3></div>
            <div v-if="versionActions.length" class="res-grid">
              <div v-for="a in versionActions" :key="a.id" class="res-card">
                <div class="res-card__top">
                  <span class="res-card__name">{{ a.name }}</span>
                  <span v-if="a.category" class="res-card__tag res-card__tag--plain">{{ formatCategory(a.category) }}</span>
                </div>
                <span class="res-card__en">{{ a.action_type || '—' }}</span>
                <p v-if="a.description" class="res-card__desc">{{ a.description }}</p>
              </div>
            </div>
            <div v-else class="res-empty">暂无动作</div>
          </section>

          <div v-if="checkResult" class="check-card">
            <h3>一致性检查</h3>
            <div class="check-card__summary" :class="checkResult.passed ? 'check-card__summary--pass' : 'check-card__summary--fail'">{{ checkResult.summary }}</div>
            <div v-if="checkResult.entity_issues.length || checkResult.relation_issues.length" class="check-card__issues">
              <div v-for="(iss, i) in checkResult.entity_issues" :key="'e'+i" class="issue-item">{{ iss.entity_name }}: {{ iss.issues.join(', ') }}</div>
              <div v-for="(iss, i) in checkResult.relation_issues" :key="'r'+i" class="issue-item issue-item--rel">{{ iss.issue }}</div>
            </div>
          </div>

          <div class="action-bar">
            <template v-if="detail.status === 'draft'">
              <button class="btn-quiet" @click="runCheck" :disabled="loading">一致性检查</button>
              <button class="btn-quiet" @click="submitForApproval" :disabled="loading || !detail.entities.length">提交审批</button>
              <button class="btn-quiet" @click="previewImpact">预览影响</button>
              <button class="btn-quiet btn-quiet--danger" @click="deleteVersion">删除草稿</button>
            </template>
            <template v-else-if="detail.status === 'pending_approval'">
              <button class="btn-quiet" @click="approveVersion" :disabled="loading">审批通过</button>
              <button class="btn-quiet btn-quiet--danger" @click="showRejectDialog = true">驳回</button>
              <button class="btn-quiet" @click="previewImpact">预览影响</button>
            </template>
            <template v-else-if="detail.status === 'published'">
              <button class="btn-quiet" @click="rollbackVersion" :disabled="loading">回滚到此版本</button>
            </template>
          </div>
        </template>
        <div v-else class="version-empty-main"><span>← 选择一个版本查看详情</span></div>
      </div>
    </div>
    <!-- 创建版本弹窗 -->
    <div v-if="showCreateDialog" class="modal-overlay" @click.self="showCreateDialog = false">
      <div class="modal-box">
        <h3>创建新版本</h3>
        <div class="form-group"><label>版本名称</label><input v-model="newVersion.name" placeholder="如: 2024Q1 发布" /></div>
        <div class="form-group"><label>描述</label><textarea v-model="newVersion.description" rows="3" placeholder="可选"></textarea></div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreateDialog = false">取消</button>
          <button class="btn-primary" :disabled="!newVersion.name.trim()" @click="createVersion">创建</button>
        </div>
      </div>
    </div>

    <!-- 添加实体弹窗 -->
    <div v-if="showEntitySelector" class="modal-overlay" @click.self="showEntitySelector = false">
      <div class="modal-box modal-box--wide">
        <h3>选择实体</h3>
        <div class="selector-list">
          <label v-for="e in availableEntities" :key="e.id" class="selector-item">
            <input type="checkbox" :value="e.id" v-model="selectedEntityIds" />
            <span class="selector-item__name">{{ e.name_cn }}</span>
            <span class="selector-item__en">{{ e.name }}</span>
            <span class="selector-item__tier">T{{ e.tier }}</span>
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showEntitySelector = false">取消</button>
          <button class="btn-primary" :disabled="!selectedEntityIds.length" @click="addEntities">添加 ({{ selectedEntityIds.length }})</button>
        </div>
      </div>
    </div>

    <!-- 驳回弹窗 -->
    <div v-if="showRejectDialog" class="modal-overlay" @click.self="showRejectDialog = false">
      <div class="modal-box">
        <h3>驳回版本</h3>
        <div class="form-group"><label>驳回原因</label><textarea v-model="rejectReason" rows="3" placeholder="请说明驳回原因"></textarea></div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showRejectDialog = false">取消</button>
          <button class="btn-danger" :disabled="!rejectReason.trim()" @click="rejectVersion">驳回</button>
        </div>
      </div>
    </div>

    <!-- 影响面预览 -->
    <div v-if="showImpact" class="impact-overlay" @click.self="showImpact = false">
      <div class="impact-dialog">
        <div class="impact-dialog__header"><h3>发布影响预览</h3><button class="impact-dialog__close" @click="showImpact = false">&times;</button></div>
        <div class="impact-dialog__body">
          <div v-if="impactLoading" class="impact-dialog__loading">加载中...</div>
          <template v-else-if="impactData">
            <div v-if="!impactData.breaking_changes?.length && !impactData.affected_scenes?.length && !impactData.affected_agents?.length" class="impact-dialog__empty">无破坏性变更，可安全发布</div>
            <template v-else>
              <h4 v-if="impactData.breaking_changes?.length">破坏性变更</h4>
              <ul v-if="impactData.breaking_changes?.length" class="impact-dialog__list"><li v-for="(c, i) in impactData.breaking_changes" :key="i"><span :class="c.type === 'removed' ? 'impact-dialog__tag--del' : 'impact-dialog__tag--ren'">{{ c.type === 'removed' ? '删除' : '重命名' }}</span> {{ c.name }}</li></ul>
              <h4 v-if="impactData.affected_scenes?.length">受影响场景 ({{ impactData.affected_scenes.length }})</h4>
              <ul v-if="impactData.affected_scenes?.length" class="impact-dialog__list"><li v-for="s in impactData.affected_scenes" :key="s.id">{{ s.name }}</li></ul>
              <h4 v-if="impactData.affected_agents?.length">受影响智能体 ({{ impactData.affected_agents.length }})</h4>
              <ul v-if="impactData.affected_agents?.length" class="impact-dialog__list"><li v-for="a in impactData.affected_agents" :key="a.id">{{ a.name }}</li></ul>
            </template>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { get, post, del } from '../../api/client'
import { ontologyPublishApi } from '../../api/aip'

interface OntologyCard {
  ontology_id: string; code: string; name: string; color: string | null
  description: string | null; active_version: VersionInfo | null
  total_versions: number; versions: VersionInfo[]
}

interface VersionInfo {
  id: string; version_number: number; name: string; status: string
  entity_count: number; published_at: string | null; is_active: boolean
}

interface VersionSummary {
  id: string; version_number: number; name: string; description: string | null
  status: string; entity_count: number; created_by: string | null
  created_at: string | null; submitted_at: string | null; published_at: string | null
  is_active: boolean; rollback_from: number | null
}

interface Readiness { has_datasource: boolean; mapped_attrs: number; total_attrs: number; mapping_ratio: number; issues: string[]; ready: boolean }
interface VersionEntity { id: string; source_entity_id: string; name: string; name_cn: string; tier: number; description: string | null; attribute_count: number; mapped_count: number; readiness: Readiness }
interface VersionDetail extends VersionSummary { rejected_at: string | null; reject_reason: string | null; approved_by: string | null; entities: VersionEntity[]; relations: any[] }
interface CheckResult { passed: boolean; entity_issues: any[]; relation_issues: any[]; summary: string }
interface EntityItem { id: string; name: string; name_cn: string; tier: number }

const ontologies = ref<OntologyCard[]>([])
const selectedOntology = ref<OntologyCard | null>(null)
const versions = ref<VersionSummary[]>([])
const selectedVersionId = ref<string | null>(null)
const detail = ref<VersionDetail | null>(null)
const versionFunctions = ref<any[]>([])
const versionActions = ref<any[]>([])
const checkResult = ref<CheckResult | null>(null)
const loading = ref(false)

const showCreateDialog = ref(false)
const showEntitySelector = ref(false)
const showRejectDialog = ref(false)
const showImpact = ref(false)
const impactData = ref<any>(null)
const impactLoading = ref(false)

const newVersion = reactive({ name: '', description: '' })
const rejectReason = ref('')
const selectedEntityIds = ref<string[]>([])
const allEntities = ref<EntityItem[]>([])

const filteredVersions = computed(() => {
  if (!selectedOntology.value) return versions.value
  return selectedOntology.value.versions.map(v => ({
    ...v, description: null, created_by: null, created_at: null, submitted_at: null,
    rollback_from: null,
  } as VersionSummary))
})

const availableEntities = computed(() => {
  if (!detail.value) return allEntities.value
  const inVersion = new Set(detail.value.entities.map(e => e.source_entity_id))
  return allEntities.value.filter(e => !inVersion.has(e.id))
})

onMounted(async () => {
  await loadOntologies()
})

async function loadOntologies() {
  loading.value = true
  try {
    ontologies.value = await ontologyPublishApi.listPublishedOntologies()
  } finally {
    loading.value = false
  }
}

function selectOntology(onto: OntologyCard) {
  selectedOntology.value = onto
  selectedVersionId.value = null
  detail.value = null
  checkResult.value = null
  loadAllEntities()
  if (onto.active_version) {
    selectVersion(onto.active_version.id)
  }
}

function backToGrid() {
  selectedOntology.value = null
  selectedVersionId.value = null
  detail.value = null
  versionFunctions.value = []
  versionActions.value = []
  checkResult.value = null
  loadOntologies()
}
async function loadAllEntities() {
  const list = await get<{ items?: any[] } | any[]>('/entities')
  const items = Array.isArray(list) ? list : (list.items || [])
  allEntities.value = items.map((e: any) => ({ id: e.id, name: e.name, name_cn: e.name_cn, tier: e.tier }))
}

async function selectVersion(id: string) {
  selectedVersionId.value = id
  checkResult.value = null
  versionFunctions.value = []
  versionActions.value = []
  detail.value = await get(`/ontology-publish/versions/${id}`)
  const [fns, acts] = await Promise.all([
    ontologyPublishApi.listVersionFunctions(id).catch(() => []),
    ontologyPublishApi.listVersionActions(id).catch(() => []),
  ])
  versionFunctions.value = fns || []
  versionActions.value = acts || []
}

// version_entity_id / from_entity_id 等引用的是 OntologyVersionEntity.id，映射回中文名
function entityName(veId: string | null): string {
  if (!veId || !detail.value) return '—'
  const e = detail.value.entities.find(x => x.id === veId)
  return e ? e.name_cn : '—'
}

function formatCategory(cat: string): string {
  const map: Record<string, string> = { domain: '领域', system: '系统' }
  return map[cat] || cat
}

async function createVersion() {
  const v = await post<{ id: string }>('/ontology-publish/versions', { name: newVersion.name, description: newVersion.description || null })
  showCreateDialog.value = false
  newVersion.name = ''
  newVersion.description = ''
  await loadOntologies()
  if (selectedOntology.value) {
    const updated = ontologies.value.find(o => o.ontology_id === selectedOntology.value!.ontology_id)
    if (updated) selectedOntology.value = updated
  }
  await selectVersion(v.id)
}

async function deleteVersion() {
  if (!detail.value) return
  await del(`/ontology-publish/versions/${detail.value.id}`)
  detail.value = null
  selectedVersionId.value = null
  await loadOntologies()
  if (selectedOntology.value) {
    const updated = ontologies.value.find(o => o.ontology_id === selectedOntology.value!.ontology_id)
    if (updated) selectedOntology.value = updated
  }
}

async function addEntities() {
  if (!detail.value) return
  loading.value = true
  await post(`/ontology-publish/versions/${detail.value.id}/entities`, { entity_ids: selectedEntityIds.value })
  selectedEntityIds.value = []
  showEntitySelector.value = false
  await selectVersion(detail.value.id)
  loading.value = false
}

async function removeEntity(entityId: string) {
  if (!detail.value) return
  await del(`/ontology-publish/versions/${detail.value.id}/entities/${entityId}`)
  await selectVersion(detail.value.id)
}

async function runCheck() {
  if (!detail.value) return
  loading.value = true
  checkResult.value = await get(`/ontology-publish/versions/${detail.value.id}/check`)
  loading.value = false
}

async function submitForApproval() {
  if (!detail.value) return
  loading.value = true
  try {
    await post(`/ontology-publish/versions/${detail.value.id}/submit`)
    await loadOntologies()
    await selectVersion(detail.value.id)
  } catch (e: any) {
    checkResult.value = { passed: false, entity_issues: [], relation_issues: [], summary: e?.response?.data?.detail || '提交失败' }
  }
  loading.value = false
}

async function approveVersion() {
  if (!detail.value) return
  loading.value = true
  await post(`/ontology-publish/versions/${detail.value.id}/approve`)
  await loadOntologies()
  await selectVersion(detail.value.id)
  loading.value = false
}

async function rejectVersion() {
  if (!detail.value) return
  await post(`/ontology-publish/versions/${detail.value.id}/reject`, { reason: rejectReason.value })
  rejectReason.value = ''
  showRejectDialog.value = false
  await loadOntologies()
  await selectVersion(detail.value.id)
}

async function rollbackVersion() {
  if (!detail.value) return
  loading.value = true
  const v = await post<{ id: string }>(`/ontology-publish/versions/${detail.value.id}/rollback`)
  await loadOntologies()
  await selectVersion(v.id)
  loading.value = false
}

async function previewImpact() {
  if (!detail.value) return
  showImpact.value = true
  impactLoading.value = true
  try {
    impactData.value = await ontologyPublishApi.previewImpact(detail.value.id)
  } catch { impactData.value = null }
  finally { impactLoading.value = false }
}

function formatStatus(status: string) {
  const map: Record<string, string> = { draft: '草稿', pending_approval: '待审批', published: '已发布', rejected: '已驳回' }
  return map[status] || status
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>
<style scoped>
.publish-page { padding: 24px; height: 100%; display: flex; flex-direction: column; }
.publish-page__header { margin-bottom: 20px; }
.publish-page__title-row { display: flex; align-items: center; gap: 12px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 4px 0 0; }
.btn-back { background: none; border: 1px solid var(--neutral-200); padding: 4px 12px; border-radius: 6px; font-size: 13px; cursor: pointer; color: var(--neutral-600); }
.btn-back:hover { background: var(--neutral-50); }

/* 卡片网格 */
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
@media (max-width: 1100px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px) { .card-grid { grid-template-columns: 1fr; } }

.onto-card { background: #fff; border: 1px solid var(--neutral-100); border-radius: 12px; padding: 20px; cursor: pointer; transition: all 0.15s; display: flex; flex-direction: column; gap: 12px; }
.onto-card:hover { border-color: var(--semantic-400); box-shadow: 0 4px 12px rgba(59,130,246,0.08); }
.onto-card__top { display: flex; align-items: center; gap: 12px; }
.onto-card__icon { width: 40px; height: 40px; border-radius: 10px; background: var(--semantic-50); color: var(--semantic-600); display: flex; align-items: center; justify-content: center; }
.onto-card__info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.onto-card__name { font-size: 15px; font-weight: 600; color: var(--neutral-900); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.onto-card__code { font-size: 11px; color: var(--neutral-400); }
.onto-card__badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: #dcfce7; color: #166534; }
.onto-card__desc { font-size: 13px; color: var(--neutral-500); line-height: 1.4; margin: 0; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.onto-card__stats { display: flex; gap: 16px; font-size: 12px; color: var(--neutral-600); padding-top: 8px; border-top: 1px solid var(--neutral-50); }
.onto-card__footer { display: flex; justify-content: space-between; align-items: center; font-size: 11px; }
.onto-card__status { color: #166534; font-weight: 600; }
.onto-card__time { color: var(--neutral-400); }

.empty-state { grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--neutral-400); }
.empty-state p { margin: 4px 0; }
.empty-state__hint { font-size: 13px; }

/* 版本详情布局 */
.publish-page__body { display: flex; gap: 20px; flex: 1; min-height: 0; }
.version-sidebar { width: 280px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; }
.version-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.version-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; cursor: pointer; border: 1px solid var(--neutral-100); transition: all 0.15s; }
.version-item:hover { background: var(--neutral-50); }
.version-item--active { background: var(--semantic-50); border-color: var(--semantic-200); }
.version-item__badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: var(--neutral-100); color: var(--neutral-600); }
.version-item__badge--published { background: #dcfce7; color: #166534; }
.version-item__badge--pending_approval { background: #fef3c7; color: #92400e; }
.version-item__badge--rejected { background: #fee2e2; color: #991b1b; }
.version-item__badge--draft { background: #e0e7ff; color: #3730a3; }
.version-item__info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.version-item__name { font-size: 13px; font-weight: 500; color: var(--neutral-800); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.version-item__meta { font-size: 11px; color: var(--neutral-500); }
.version-item__active { font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 3px; background: #dcfce7; color: #166534; }
.version-empty { font-size: 13px; color: var(--neutral-400); text-align: center; padding: 20px; }

.version-main { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.version-empty-main { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--neutral-400); }

.meta-card { background: var(--neutral-50); border-radius: 10px; padding: 16px; }
.meta-card__header { display: flex; align-items: center; gap: 10px; }
.meta-card__header h2 { font-size: 16px; font-weight: 600; margin: 0; color: var(--neutral-900); }
.meta-card__desc { font-size: 13px; color: var(--neutral-600); margin: 8px 0 0; }
.meta-card__timeline { display: flex; gap: 16px; margin-top: 10px; font-size: 11px; color: var(--neutral-500); }
.meta-card__reject { margin-top: 8px; padding: 8px 10px; background: #fef2f2; border-radius: 6px; font-size: 12px; color: #dc2626; }

.status-tag { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.status-tag--draft { background: #e0e7ff; color: #3730a3; }
.status-tag--pending_approval { background: #fef3c7; color: #92400e; }
.status-tag--published { background: #dcfce7; color: #166534; }
.status-tag--rejected { background: #fee2e2; color: #991b1b; }

/* 资源统计概览 */
.meta-card__stats { display: flex; gap: 28px; margin-top: 14px; }
.res-stat { display: flex; flex-direction: column; gap: 2px; }
.res-stat__value { font-size: 20px; font-weight: 700; color: var(--neutral-900); line-height: 1; }
.res-stat__label { font-size: 11px; color: var(--neutral-500); }

/* 分类资源区 */
.res-section { display: flex; flex-direction: column; gap: 12px; }
.res-section__header { display: flex; align-items: center; justify-content: space-between; }
.res-section__header h3 { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; margin: 0; color: var(--neutral-800); }
.res-section__count { font-size: 11px; font-weight: 700; padding: 1px 8px; border-radius: 10px; background: var(--neutral-100); color: var(--neutral-600); }

.res-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.res-card { background: #fff; border: 1px solid var(--neutral-100); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 6px; transition: all 0.15s; }
.res-card:hover { border-color: var(--semantic-400); box-shadow: 0 4px 12px rgba(59,130,246,0.08); }
.res-card__top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.res-card__name { font-size: 14px; font-weight: 600; color: var(--neutral-900); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.res-card__en { font-size: 11px; color: var(--neutral-400); }
.res-card__desc { font-size: 12px; color: var(--neutral-500); line-height: 1.4; margin: 0; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.res-card__foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 2px; padding-top: 8px; border-top: 1px solid var(--neutral-50); }
.res-card__tag { font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 4px; background: var(--semantic-50); color: var(--semantic-600); white-space: nowrap; }
.res-card__tag--plain { background: var(--neutral-100); color: var(--neutral-600); }
.res-card__rel { font-size: 12px; color: var(--neutral-600); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.res-empty { font-size: 13px; color: var(--neutral-400); text-align: center; padding: 24px; border: 1px dashed var(--neutral-200); border-radius: 10px; }

.check-card { background: #fff; border: 1px solid var(--neutral-100); border-radius: 10px; padding: 16px; }
.check-card h3 { font-size: 14px; font-weight: 600; margin: 0 0 10px; }
.check-card__summary { font-size: 13px; font-weight: 600; padding: 8px 12px; border-radius: 6px; }
.check-card__summary--pass { background: #dcfce7; color: #166534; }
.check-card__summary--fail { background: #fef2f2; color: #dc2626; }
.check-card__issues { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.issue-item { font-size: 12px; color: #dc2626; padding: 4px 8px; background: #fef2f2; border-radius: 4px; }
.issue-item--rel { color: #92400e; background: #fef3c7; }

.action-bar { display: flex; gap: 8px; align-items: center; padding-top: 12px; margin-top: 4px; border-top: 1px solid var(--neutral-100); flex-wrap: wrap; }

/* 弱化的审批操作按钮 */
.btn-quiet { padding: 5px 12px; border-radius: 6px; border: 1px solid var(--neutral-200); background: #fff; color: var(--neutral-600); font-size: 12px; cursor: pointer; transition: all 0.15s; }
.btn-quiet:hover:not(:disabled) { border-color: var(--semantic-400); color: var(--semantic-600); }
.btn-quiet:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-quiet--danger { color: #b91c1c; }
.btn-quiet--danger:hover:not(:disabled) { border-color: #fca5a5; color: #dc2626; }

.btn-primary { padding: 8px 18px; border-radius: 6px; border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 8px 18px; border-radius: 6px; border: 1px solid var(--neutral-200); background: #fff; color: var(--neutral-700); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50); }
.btn-danger { padding: 8px 18px; border-radius: 6px; border: none; background: #dc2626; color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-danger:hover:not(:disabled) { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger-outline { padding: 8px 18px; border-radius: 6px; border: 1px solid #fca5a5; background: #fef2f2; color: #dc2626; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-danger-outline:hover { background: #fee2e2; }
.btn-outline { padding: 8px 18px; border-radius: 6px; border: 1px solid var(--neutral-300); background: #fff; color: var(--neutral-700); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-outline:hover { background: var(--neutral-50); }
.btn-sm { padding: 4px 12px; border-radius: 5px; border: 1px solid var(--neutral-200); background: #fff; font-size: 12px; cursor: pointer; }
.btn-sm:hover { background: var(--neutral-50); }
.btn-block { width: 100%; }
.btn-link { background: none; border: none; font-size: 12px; cursor: pointer; color: var(--semantic-600); }
.btn-link--danger { color: #dc2626; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-box { background: #fff; border-radius: 12px; padding: 24px; width: 400px; max-height: 80vh; overflow-y: auto; }
.modal-box--wide { width: 520px; }
.modal-box h3 { font-size: 16px; font-weight: 600; margin: 0 0 16px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--neutral-600); margin-bottom: 4px; }
.form-group input, .form-group textarea { width: 100%; padding: 8px 10px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 13px; resize: vertical; }

.selector-list { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.selector-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.selector-item:hover { background: var(--neutral-50); }
.selector-item input { margin: 0; }
.selector-item__name { font-weight: 500; }
.selector-item__en { color: var(--neutral-400); font-size: 11px; }
.selector-item__tier { margin-left: auto; font-size: 11px; color: var(--neutral-500); }

.impact-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.impact-dialog { background: #fff; border-radius: 8px; width: 480px; max-height: 70vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.impact-dialog__header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #e5e7eb; }
.impact-dialog__header h3 { margin: 0; font-size: 16px; }
.impact-dialog__close { background: none; border: none; font-size: 20px; cursor: pointer; color: #6b7280; }
.impact-dialog__body { padding: 16px 20px; }
.impact-dialog__body h4 { margin: 12px 0 6px; font-size: 13px; color: #374151; }
.impact-dialog__list { margin: 0; padding-left: 16px; font-size: 13px; }
.impact-dialog__list li { margin: 4px 0; }
.impact-dialog__loading { text-align: center; color: #6b7280; padding: 20px; }
.impact-dialog__empty { text-align: center; color: #059669; padding: 20px; }
.impact-dialog__tag--del { color: #dc2626; }
.impact-dialog__tag--ren { color: #d97706; }
</style>





