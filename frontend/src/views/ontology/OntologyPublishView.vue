<template>
  <div class="publish-page">
    <!-- 顶部 Banner，与本体列表风格一致 -->
    <div class="page-banner">
      <div class="page-banner__content">
        <div class="page-banner__title-row">
          <button v-if="selectedOntology" class="btn-back" @click="backToGrid()" :disabled="saving">&larr; 返回</button>
          <h1 class="page-banner__title">{{ selectedOntology ? selectedOntology.name : '本体发布环境' }}</h1>
        </div>
        <p class="page-banner__desc">{{ selectedOntology ? `版本历史 · 共 ${selectedOntology.total_versions} 个版本` : '已发布本体一览，点击卡片查看版本历史' }}</p>
      </div>
    </div>

    <div v-if="catalogError" class="load-state" role="alert"><p>{{ catalogError }}</p><button class="btn-secondary" @click="loadOntologies">重新加载</button></div>
    <div v-if="!selectedOntology && catalogLoading" class="load-state" role="status">本体版本加载中...</div>
    <!-- 第一级：本体卡片网格 -->
    <div v-if="!selectedOntology" class="card-grid">
      <div
        v-for="onto in ontologies"
        :key="onto.ontology_id"
        class="onto-card"
        role="button" tabindex="0"
        @keydown.enter="selectOntology(onto)" @keydown.space.prevent="selectOntology(onto)"
        @click="selectOntology(onto)"
      >
        <div class="onto-card__top">
          <div class="onto-card__icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </div>
          <div class="onto-card__info">
            <span class="onto-card__name" :title="onto.name">{{ onto.name }}</span>
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
          <span class="onto-card__status">{{ onto.active_version ? '已发布' : '暂无在线版本' }}</span>
          <span class="onto-card__time">{{ onto.active_version?.published_at ? formatTime(onto.active_version.published_at) : '—' }}</span>
        </div>
      </div>
      <div v-if="!ontologies.length && !loading && !catalogError" class="empty-state">
        <p>暂无已发布的本体</p>
        <p class="empty-state__hint">在本体详情页点击"发布"按钮即可发布本体</p>
      </div>
    </div>

    <!-- 第二级：版本历史详情 -->
    <div v-if="selectedOntology" class="publish-page__body">
      <div class="version-sidebar">
        <button class="btn-primary btn-block" :disabled="!canEdit || (loading)" @click="showCreateDialog = true">创建新版本</button>
        <div class="version-list">
          <div
            v-for="v in filteredVersions"
            :key="v.id"
            class="version-item" role="button" tabindex="0"
            :aria-current="selectedVersionId === v.id ? 'true' : undefined"
            @keydown.enter="!saving && selectVersion(v.id)" @keydown.space.prevent="!saving && selectVersion(v.id)"
            :class="{ 'version-item--active': selectedVersionId === v.id }"
            @click="!saving && selectVersion(v.id)"
          >
            <div class="version-item__badge" :class="`version-item__badge--${v.status}`">v{{ v.version_number }}</div>
            <div class="version-item__info">
              <span class="version-item__name" :title="v.name">{{ v.name }}</span>
              <span class="version-item__meta">{{ v.entity_count }} 个实体 · {{ formatStatus(v.status) }}</span>
            </div>
            <span v-if="v.is_active" class="version-item__active">当前</span>
          </div>
          <div v-if="!filteredVersions.length" class="version-empty">暂无版本</div>
        </div>
      </div>

      <div class="version-main">
        <div v-if="detailLoading" class="load-state" role="status">版本详情加载中...</div>
        <div v-else-if="detailError" class="load-state" role="alert"><p>{{ detailError }}</p><button class="btn-secondary" @click="selectedVersionId && selectVersion(selectedVersionId)">重新加载</button></div>
        <template v-else-if="detail">
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
              <button v-if="detail.status === 'draft'" class="btn-link" @click="showEntitySelector = true" :disabled="!canEdit || (loading)">+ 添加实体</button>
            </div>
            <div v-if="detail.entities.length" class="res-grid">
              <div v-for="e in detail.entities" :key="e.id" class="res-card">
                <div class="res-card__top">
                  <span class="res-card__name">{{ e.name_cn }}</span>
                </div>
                <span class="res-card__en">{{ e.name }}</span>
                <p v-if="e.description" class="res-card__desc">{{ e.description }}</p>
                <div class="res-card__foot">
                  <span class="res-card__tag">属性 {{ e.attribute_count }}</span>
                  <button v-if="detail.status === 'draft'" class="btn-link btn-link--danger" @click="removeEntity(e.source_entity_id)" :disabled="!canEdit || (loading)">移除</button>
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
              <button class="btn-quiet" @click="submitForApproval" :disabled="!canEdit || (loading || !detail.entities.length)">提交审批</button>
              <button class="btn-quiet" @click="previewImpact" :disabled="loading">预览影响</button>
              <button class="btn-quiet btn-quiet--danger" @click="deleteVersion" :disabled="!canEdit || (loading)">删除草稿</button>
            </template>
            <template v-else-if="detail.status === 'pending_approval'">
              <button class="btn-quiet" @click="approveVersion" :disabled="!canEdit || (loading)">审批通过</button>
              <button class="btn-quiet btn-quiet--danger" @click="showRejectDialog = true" :disabled="!canEdit || (loading)">驳回</button>
              <button class="btn-quiet" @click="previewImpact" :disabled="loading">预览影响</button>
            </template>
            <template v-else-if="detail.status === 'published'">
              <button class="btn-quiet" @click="rollbackVersion" :disabled="!canEdit || (loading)">回滚到此版本</button>
            </template>
          </div>
        </template>
        <div v-else class="version-empty-main"><span>← 选择一个版本查看详情</span></div>
      </div>
    </div>
    <ModalDialog :visible="showCreateDialog" title="创建新版本" width="400px" @close="!saving && (showCreateDialog = false)">
      <div class="form-group"><label for="version-name">版本名称</label><input id="version-name" maxlength="200" v-model="newVersion.name" placeholder="请输入版本名称" /></div>
      <div class="form-group"><label for="version-description">描述</label><textarea id="version-description" v-model="newVersion.description" rows="3" placeholder="可选"></textarea></div>
      <template #footer>
        <button class="btn-secondary" :disabled="saving" @click="showCreateDialog = false">取消</button>
        <button class="btn-primary" :disabled="!canEdit || (loading || !newVersion.name.trim())" @click="createVersion">{{ saving ? '创建中…' : '创建' }}</button>
      </template>
    </ModalDialog>

    <ModalDialog :visible="showEntitySelector" title="选择实体" width="520px" @close="!saving && (showEntitySelector = false)">
      <div class="selector-list">
        <p v-if="!availableEntities.length" class="res-empty">当前本体暂无可添加对象</p>
        <label v-for="e in availableEntities" :key="e.id" class="selector-item">
          <input type="checkbox" :value="e.id" v-model="selectedEntityIds" :disabled="saving" />
          <span class="selector-item__name">{{ e.name_cn }}</span>
          <span class="selector-item__en">{{ e.name }}</span>
          <span class="selector-item__tier">T{{ e.tier }}</span>
        </label>
      </div>
      <template #footer>
        <button class="btn-secondary" :disabled="saving" @click="showEntitySelector = false">取消</button>
        <button class="btn-primary" :disabled="!canEdit || (loading || !selectedEntityIds.length)" @click="addEntities">{{ saving ? '添加中…' : `添加 (${selectedEntityIds.length})` }}</button>
      </template>
    </ModalDialog>

    <ModalDialog :visible="showRejectDialog" title="驳回版本" width="400px" @close="!saving && (showRejectDialog = false)">
      <div class="form-group"><label for="version-reject-reason">驳回原因</label><textarea id="version-reject-reason" v-model="rejectReason" rows="3" placeholder="请说明驳回原因"></textarea></div>
      <template #footer>
        <button class="btn-secondary" :disabled="saving" @click="showRejectDialog = false">取消</button>
        <button class="btn-danger" :disabled="!canEdit || (loading || !rejectReason.trim())" @click="rejectVersion">{{ saving ? '提交中…' : '驳回' }}</button>
      </template>
    </ModalDialog>

    <ModalDialog :visible="showImpact" title="发布影响预览" width="780px" @close="closeImpact">
      <div v-if="impactLoading" class="impact-dialog__loading">加载中...</div>
      <div v-else-if="impactError" class="load-state" role="alert"><p>{{ impactError }}</p><button class="btn-secondary" @click="previewImpact">重新加载</button></div>
      <template v-else-if="impactData">
        <div v-if="!impactData.breaking_changes?.length && !impactData.affected_scenes?.length && !impactData.affected_agents?.length" class="impact-dialog__empty">无破坏性变更，可安全发布</div>
        <template v-else>
          <h4 v-if="impactData.breaking_changes?.length">破坏性变更</h4>
          <ul v-if="impactData.breaking_changes?.length" class="impact-dialog__list"><li v-for="(c, i) in impactData.breaking_changes" :key="i"><span :class="c.type === 'removed' ? 'impact-dialog__tag--del' : 'impact-dialog__tag--ren'">{{ c.type === 'removed' ? '删除' : '重命名' }}</span> {{ c.name }}</li></ul>
          <h4 v-if="impactData.affected_scenes?.length">受影响场景 ({{ impactData.affected_scenes.length }})</h4>
          <ul v-if="impactData.affected_scenes?.length" class="impact-dialog__list"><li v-for="item in impactData.affected_scenes" :key="item.id">{{ item.name }}</li></ul>
          <h4 v-if="impactData.affected_agents?.length">受影响智能体 ({{ impactData.affected_agents.length }})</h4>
          <ul v-if="impactData.affected_agents?.length" class="impact-dialog__list"><li v-for="item in impactData.affected_agents" :key="item.id">{{ item.name }}</li></ul>
        </template>
      </template>
      <template #footer><button class="btn-secondary" @click="closeImpact">关闭</button></template>
    </ModalDialog>
  </div>
</template>
<script setup lang="ts">
import { formatPlatformDateTime } from '../../utils/platformTime'
import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('entity:write')
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { get, post, del } from '../../api/client'
import { ontologyPublishApi } from '../../api/ontologyPublish'
import { message } from 'ant-design-vue'
import ModalDialog from '../../components/common/ModalDialog.vue'

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

const route = useRoute()
const ontologies = ref<OntologyCard[]>([])
const selectedOntology = ref<OntologyCard | null>(null)
const versions = ref<VersionSummary[]>([])
const selectedVersionId = ref<string | null>(null)
const detail = ref<VersionDetail | null>(null)
const versionFunctions = ref<any[]>([])
const versionActions = ref<any[]>([])
const checkResult = ref<CheckResult | null>(null)
const catalogLoading = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const loading = computed(() => catalogLoading.value || detailLoading.value || saving.value)
const catalogError = ref('')
const detailError = ref('')
const impactError = ref('')
let catalogRequest = 0
let versionRequest = 0
let entitiesRequest = 0
let impactRequest = 0

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
  const ontology = ontologies.value.find(item => item.ontology_id === route.query.ontology_id)
  if (ontology) {
    selectOntology(ontology)
    if (route.query.version_id) await selectVersion(route.query.version_id as string)
  }
})

function errorText(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' ? detail : error?.message || fallback
}

function resetDialogs() {
  showCreateDialog.value = false
  showEntitySelector.value = false
  showRejectDialog.value = false
  showImpact.value = false
  selectedEntityIds.value = []
  rejectReason.value = ''
  newVersion.name = ''
  newVersion.description = ''
  impactData.value = null
  impactError.value = ''
  ++impactRequest
}

async function loadOntologies() {
  const request = ++catalogRequest
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const items = await ontologyPublishApi.listPublishedOntologies()
    if (request !== catalogRequest) return
    ontologies.value = items
    if (selectedOntology.value) {
      const updated = items.find((o: OntologyCard) => o.ontology_id === selectedOntology.value?.ontology_id)
      if (updated) selectedOntology.value = updated
      else backToGrid(false)
    }
  } catch (error) {
    if (request === catalogRequest) catalogError.value = errorText(error, '本体版本加载失败')
  } finally {
    if (request === catalogRequest) catalogLoading.value = false
  }
}

function selectOntology(onto: OntologyCard) {
  if (saving.value) return
  ++versionRequest
  detailLoading.value = false
  selectedOntology.value = onto
  selectedVersionId.value = null
  detail.value = null
  detailError.value = ''
  checkResult.value = null
  resetDialogs()
  loadAllEntities()
  const initialVersion = onto.active_version || onto.versions[0]
  if (initialVersion) selectVersion(initialVersion.id)
}

function backToGrid(reload = true) {
  if (saving.value && reload) return
  ++versionRequest
  ++entitiesRequest
  detailLoading.value = false
  selectedOntology.value = null
  selectedVersionId.value = null
  detail.value = null
  detailError.value = ''
  versionFunctions.value = []
  versionActions.value = []
  checkResult.value = null
  resetDialogs()
  if (reload) loadOntologies()
}

async function loadAllEntities() {
  const ontologyId = selectedOntology.value?.ontology_id
  if (!ontologyId) return
  const request = ++entitiesRequest
  allEntities.value = []
  try {
    const list = await get<{ items?: any[] } | any[]>('/entities', { params: { ontology_id: ontologyId } })
    if (request !== entitiesRequest || selectedOntology.value?.ontology_id !== ontologyId) return
    const items = Array.isArray(list) ? list : (list.items || [])
    allEntities.value = items.map((e: any) => ({ id: e.id, name: e.name, name_cn: e.name_cn, tier: e.tier }))
  } catch (error) {
    if (request === entitiesRequest) message.error(errorText(error, '可添加对象加载失败'))
  }
}

async function selectVersion(id: string) {
  const request = ++versionRequest
  selectedVersionId.value = id
  detail.value = null
  detailError.value = ''
  detailLoading.value = true
  checkResult.value = null
  versionFunctions.value = []
  versionActions.value = []
  resetDialogs()
  try {
    const [version, fns, acts] = await Promise.all([
      get<VersionDetail>(`/ontology-publish/versions/${id}`),
      ontologyPublishApi.listVersionFunctions(id),
      ontologyPublishApi.listVersionActions(id),
    ])
    if (request !== versionRequest) return
    detail.value = version
    versionFunctions.value = fns || []
    versionActions.value = acts || []
  } catch (error) {
    if (request === versionRequest) detailError.value = errorText(error, '版本详情加载失败')
  } finally {
    if (request === versionRequest) detailLoading.value = false
  }
}

async function performMutation(task: () => Promise<void>, success: string) {
  if (saving.value || detailLoading.value) return
  saving.value = true
  try {
    await task()
    message.success(success)
  } catch (error) {
    message.error(errorText(error, '操作失败，请重试'))
  } finally {
    saving.value = false
  }
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
  const ontologyId = selectedOntology.value?.ontology_id
  const name = newVersion.name.trim()
  if (!ontologyId || !name) return
  await performMutation(async () => {
    const version = await post<{ id: string }>('/ontology-publish/versions', {
      ontology_id: ontologyId, name, description: newVersion.description.trim() || null,
    })
    resetDialogs()
    await loadOntologies()
    if (selectedOntology.value?.ontology_id === ontologyId) await selectVersion(version.id)
  }, '版本草稿已创建')
}

async function deleteVersion() {
  const id = detail.value?.id
  if (!id || !window.confirm('确定删除当前版本草稿？此操作无法撤销。')) return
  await performMutation(async () => {
    await del(`/ontology-publish/versions/${id}`)
    if (selectedVersionId.value === id) {
      ++versionRequest
      detail.value = null
      selectedVersionId.value = null
    }
    await loadOntologies()
  }, '版本草稿已删除')
}

async function refreshVersion(id: string) {
  await loadOntologies()
  if (selectedOntology.value && selectedVersionId.value === id) await selectVersion(id)
}

async function addEntities() {
  const id = detail.value?.id
  if (!id || !selectedEntityIds.value.length) return
  const entityIds = [...selectedEntityIds.value]
  await performMutation(async () => {
    await post(`/ontology-publish/versions/${id}/entities`, { entity_ids: entityIds })
    selectedEntityIds.value = []
    showEntitySelector.value = false
    await refreshVersion(id)
  }, '对象已添加到版本')
}

async function removeEntity(entityId: string) {
  const id = detail.value?.id
  if (!id) return
  await performMutation(async () => {
    await del(`/ontology-publish/versions/${id}/entities/${entityId}`)
    await refreshVersion(id)
  }, '对象已从版本移除')
}

async function runCheck() {
  const id = detail.value?.id
  if (!id) return
  await performMutation(async () => {
    const result = await get<CheckResult>(`/ontology-publish/versions/${id}/check`)
    if (selectedVersionId.value === id) checkResult.value = result
  }, '一致性检查已完成')
}

async function submitForApproval() {
  const id = detail.value?.id
  if (!id) return
  await performMutation(async () => {
    await post(`/ontology-publish/versions/${id}/submit`)
    await refreshVersion(id)
  }, '版本已提交审批')
}

async function approveVersion() {
  const id = detail.value?.id
  if (!id) return
  await performMutation(async () => {
    await post(`/ontology-publish/versions/${id}/approve`)
    await refreshVersion(id)
  }, '版本审批通过')
}

async function rejectVersion() {
  const id = detail.value?.id
  const reason = rejectReason.value.trim()
  if (!id || !reason) return
  await performMutation(async () => {
    await post(`/ontology-publish/versions/${id}/reject`, { reason })
    rejectReason.value = ''
    showRejectDialog.value = false
    await refreshVersion(id)
  }, '版本已驳回')
}

async function rollbackVersion() {
  const id = detail.value?.id
  const ontologyId = selectedOntology.value?.ontology_id
  if (!id) return
  await performMutation(async () => {
    const version = await post<{ id: string }>(`/ontology-publish/versions/${id}/rollback`)
    await loadOntologies()
    if (selectedOntology.value?.ontology_id === ontologyId) await selectVersion(version.id)
  }, '回滚版本已创建')
}

function closeImpact() {
  showImpact.value = false
  ++impactRequest
  impactLoading.value = false
}

async function previewImpact() {
  const id = detail.value?.id
  if (!id) return
  const request = ++impactRequest
  showImpact.value = true
  impactLoading.value = true
  impactData.value = null
  impactError.value = ''
  try {
    const result = await ontologyPublishApi.previewImpact(id)
    if (request === impactRequest) impactData.value = result
  } catch (error) {
    if (request === impactRequest) impactError.value = errorText(error, '影响预览加载失败，请重试')
  } finally {
    if (request === impactRequest) impactLoading.value = false
  }
}

function formatStatus(status: string) {
  const map: Record<string, string> = { draft: '草稿', pending_approval: '待审批', published: '已发布', rejected: '已驳回' }
  return map[status] || status
}

function formatTime(iso: string) {
  return formatPlatformDateTime(iso)
}
</script>
<style scoped>
.publish-page { max-width: 1400px; margin: 0 auto; height: 100%; display: flex; flex-direction: column; }

.page-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px 32px;
  background: linear-gradient(135deg, #e8f4fd 0%, #dbeafe 50%, #eff6ff 100%);
  border-radius: var(--radius-lg, 12px);
  margin-bottom: 24px;
  flex-shrink: 0;
}
.page-banner__title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.page-banner__title { font-size: 24px; font-weight: 700; color: var(--neutral-900, #111); margin: 0; }
.page-banner__desc { font-size: 13px; color: var(--neutral-600, #555); margin: 0; max-width: 600px; line-height: 1.5; }
.btn-back { background: rgba(255,255,255,0.7); border: 1px solid var(--neutral-200, #e5e5e5); padding: 5px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; color: var(--neutral-700, #333); transition: background 0.15s; }
.btn-back:hover { background: var(--neutral-0); }
.btn-back { background: none; border: 1px solid var(--neutral-200); padding: 4px 12px; border-radius: 6px; font-size: 13px; cursor: pointer; color: var(--neutral-600); }
.btn-back:hover { background: var(--neutral-50); }

/* 卡片网格 */
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
@media (max-width: 1100px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px) { .card-grid { grid-template-columns: 1fr; } }

.onto-card { background: var(--neutral-0); border: 1px solid var(--neutral-100); border-radius: 12px; padding: 20px; cursor: pointer; transition: all 0.15s; display: flex; flex-direction: column; gap: 12px; }
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

.empty-state { grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--neutral-500); }
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
.version-empty { font-size: 13px; color: var(--neutral-500); text-align: center; padding: 20px; }

.version-main { flex: 1; min-width: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.version-empty-main { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--neutral-500); }

.meta-card { background: var(--neutral-50); border-radius: 10px; padding: 16px; }
.meta-card__header { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.meta-card__header h2 { overflow-wrap: anywhere; min-width: 0; font-size: 16px; font-weight: 600; margin: 0; color: var(--neutral-900); }
.meta-card__desc { font-size: 13px; color: var(--neutral-600); margin: 8px 0 0; }
.meta-card__timeline { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 10px; font-size: 11px; color: var(--neutral-500); }
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
.res-card { background: var(--neutral-0); border: 1px solid var(--neutral-100); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 6px; transition: all 0.15s; }
.res-card:hover { border-color: var(--semantic-400); box-shadow: 0 4px 12px rgba(59,130,246,0.08); }
.res-card__top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.res-card__name { min-width: 0; font-size: 14px; font-weight: 600; color: var(--neutral-900); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.res-card__en { font-size: 11px; color: var(--neutral-400); }
.res-card__desc { font-size: 12px; color: var(--neutral-500); line-height: 1.4; margin: 0; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.res-card__foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 2px; padding-top: 8px; border-top: 1px solid var(--neutral-50); }
.res-card__tag { font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 4px; background: var(--semantic-50); color: var(--semantic-600); white-space: nowrap; }
.res-card__tag--plain { background: var(--neutral-100); color: var(--neutral-600); }
.res-card__rel { font-size: 12px; color: var(--neutral-600); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.res-empty { font-size: 13px; color: var(--neutral-500); text-align: center; padding: 24px; border: 1px dashed var(--neutral-200); border-radius: 10px; }

.check-card { background: var(--neutral-0); border: 1px solid var(--neutral-100); border-radius: 10px; padding: 16px; }
.check-card h3 { font-size: 14px; font-weight: 600; margin: 0 0 10px; }
.check-card__summary { font-size: 13px; font-weight: 600; padding: 8px 12px; border-radius: 6px; }
.check-card__summary--pass { background: #dcfce7; color: #166534; }
.check-card__summary--fail { background: #fef2f2; color: #dc2626; }
.check-card__issues { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.issue-item { font-size: 12px; color: #dc2626; padding: 4px 8px; background: #fef2f2; border-radius: 4px; }
.issue-item--rel { color: #92400e; background: #fef3c7; }

.action-bar { display: flex; gap: 8px; align-items: center; padding-top: 12px; margin-top: 4px; border-top: 1px solid var(--neutral-100); flex-wrap: wrap; }

/* 弱化的审批操作按钮 */
.btn-quiet { padding: 5px 12px; border-radius: 6px; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-600); font-size: 12px; cursor: pointer; transition: all 0.15s; }
.btn-quiet:hover:not(:disabled) { border-color: var(--semantic-400); color: var(--semantic-600); }
.btn-quiet:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-quiet--danger { color: #b91c1c; }
.btn-quiet--danger:hover:not(:disabled) { border-color: #fca5a5; color: #dc2626; }

.btn-primary { padding: 8px 18px; border-radius: 6px; border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 8px 18px; border-radius: 6px; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50); }
.btn-danger { padding: 8px 18px; border-radius: 6px; border: none; background: #dc2626; color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-danger:hover:not(:disabled) { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger-outline { padding: 8px 18px; border-radius: 6px; border: 1px solid #fca5a5; background: #fef2f2; color: #dc2626; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-danger-outline:hover { background: #fee2e2; }
.btn-outline { padding: 8px 18px; border-radius: 6px; border: 1px solid var(--neutral-300); background: var(--neutral-0); color: var(--neutral-700); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-outline:hover { background: var(--neutral-50); }
.btn-sm { padding: 4px 12px; border-radius: 5px; border: 1px solid var(--neutral-200); background: var(--neutral-0); font-size: 12px; cursor: pointer; }
.btn-sm:hover { background: var(--neutral-50); }
.btn-block { width: 100%; }
.btn-link { background: none; border: none; font-size: 12px; cursor: pointer; color: var(--semantic-600); }
.btn-link--danger { color: #dc2626; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-box { max-width: calc(100vw - 40px); background: var(--neutral-0); border-radius: 12px; padding: 24px; width: 400px; max-height: 80vh; overflow-y: auto; }
.modal-box--wide { width: 520px; }
.modal-box h3 { font-size: 16px; font-weight: 600; margin: 0 0 16px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--neutral-600); margin-bottom: 4px; }
.form-group input, .form-group textarea { background: var(--neutral-0); color: var(--neutral-800); width: 100%; padding: 8px 10px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 13px; resize: vertical; }

.selector-list { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.selector-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.selector-item:hover { background: var(--neutral-50); }
.selector-item input { margin: 0; }
.selector-item__name { font-weight: 500; }
.selector-item__en { color: var(--neutral-400); font-size: 11px; }
.selector-item__tier { margin-left: auto; font-size: 11px; color: var(--neutral-500); }

.impact-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.impact-dialog { max-width: calc(100vw - 40px); background: var(--neutral-0); border-radius: 8px; width: 480px; max-height: 70vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
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
.load-state { padding: 28px 16px; text-align: center; color: var(--neutral-600); font-size: 13px; }
.load-state p { margin: 0 0 12px; overflow-wrap: anywhere; }
.onto-card:focus-visible, .version-item:focus-visible { outline: 2px solid var(--semantic-500); outline-offset: 3px; }
.selector-item { flex-wrap: wrap; overflow-wrap: anywhere; }
@media (max-width: 1100px) {
  .version-sidebar { width: 230px; }
  .publish-page__body { gap: 16px; }
  .page-banner { padding: 24px; }
  .page-banner__title { font-size: 22px; overflow-wrap: anywhere; }
}
</style>




