<template>
  <div class="publish-page">
    <div class="publish-page__header">
      <h1 class="page-title">本体发布</h1>
      <p class="page-desc">版本化管理本体发布，支持一致性校验、审批流程和版本回滚</p>
    </div>

    <div class="publish-page__body">
      <!-- 左侧：版本时间线 -->
      <div class="version-sidebar">
        <button class="btn-primary btn-block" @click="showCreateDialog = true">创建新版本</button>
        <div class="version-list">
          <div
            v-for="v in versions"
            :key="v.id"
            class="version-item"
            :class="{ 'version-item--active': selectedVersionId === v.id }"
            @click="selectVersion(v.id)"
          >
            <div class="version-item__badge" :class="`version-item__badge--${v.status}`">
              v{{ v.version_number }}
            </div>
            <div class="version-item__info">
              <span class="version-item__name">{{ v.name }}</span>
              <span class="version-item__meta">
                {{ v.entity_count }} 个实体 · {{ formatStatus(v.status) }}
              </span>
            </div>
            <span v-if="v.is_active" class="version-item__active">当前</span>
          </div>
          <div v-if="!versions.length" class="version-empty">暂无版本</div>
        </div>
      </div>

      <!-- 右侧：版本详情 -->
      <div class="version-main">
        <template v-if="detail">
          <!-- 版本元信息 -->
          <div class="meta-card">
            <div class="meta-card__header">
              <h2>v{{ detail.version_number }} — {{ detail.name }}</h2>
              <span class="status-tag" :class="`status-tag--${detail.status}`">{{ formatStatus(detail.status) }}</span>
            </div>
            <p v-if="detail.description" class="meta-card__desc">{{ detail.description }}</p>
            <div class="meta-card__timeline">
              <span v-if="detail.created_at">创建: {{ formatTime(detail.created_at) }}</span>
              <span v-if="detail.submitted_at">提交: {{ formatTime(detail.submitted_at) }}</span>
              <span v-if="detail.published_at">发布: {{ formatTime(detail.published_at) }}</span>
              <span v-if="detail.rejected_at">驳回: {{ formatTime(detail.rejected_at) }}</span>
            </div>
            <div v-if="detail.reject_reason" class="meta-card__reject">
              驳回原因: {{ detail.reject_reason }}
            </div>
            <div v-if="detail.rollback_from" class="meta-card__rollback">
              回滚自 v{{ detail.rollback_from }}
            </div>
          </div>

          <!-- 实体列表 -->
          <div class="entity-card">
            <div class="entity-card__header">
              <h3>包含实体 ({{ detail.entities.length }})</h3>
              <button v-if="detail.status === 'draft'" class="btn-sm" @click="showEntitySelector = true">添加实体</button>
            </div>
            <div class="entity-table" v-if="detail.entities.length">
              <div class="entity-table__row entity-table__row--header">
                <span class="col-name">实体名称</span>
                <span class="col-tier">层级</span>
                <span class="col-attrs">属性</span>
                <span class="col-status">就绪</span>
                <span class="col-action" v-if="detail.status === 'draft'">操作</span>
              </div>
              <div v-for="e in detail.entities" :key="e.id" class="entity-table__row">
                <span class="col-name">
                  <strong>{{ e.name_cn }}</strong>
                  <small>{{ e.name }}</small>
                </span>
                <span class="col-tier">T{{ e.tier }}</span>
                <span class="col-attrs">{{ e.mapped_count }}/{{ e.attribute_count }}</span>
                <span class="col-status">
                  <span v-if="e.readiness.ready" class="check-pass">✓</span>
                  <span v-else class="check-fail">✗</span>
                </span>
                <span class="col-action" v-if="detail.status === 'draft'">
                  <button class="btn-link btn-link--danger" @click="removeEntity(e.source_entity_id)">移除</button>
                </span>
              </div>
            </div>
            <div v-else class="entity-empty">暂未添加实体，点击上方按钮选择</div>
          </div>

          <!-- 一致性检查 -->
          <div class="check-card" v-if="checkResult">
            <h3>一致性检查</h3>
            <div class="check-card__summary" :class="checkResult.passed ? 'check-card__summary--pass' : 'check-card__summary--fail'">
              {{ checkResult.summary }}
            </div>
            <div v-if="checkResult.entity_issues.length" class="check-card__issues">
              <div v-for="ei in checkResult.entity_issues" :key="ei.entity_id" class="issue-item">
                <strong>{{ ei.entity_name }}:</strong> {{ ei.issues.join('; ') }}
              </div>
            </div>
            <div v-if="checkResult.relation_issues.length" class="check-card__issues">
              <div v-for="ri in checkResult.relation_issues" :key="ri.relation_name" class="issue-item issue-item--rel">
                {{ ri.issue }}
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="action-bar">
            <template v-if="detail.status === 'draft'">
              <button class="btn-secondary" @click="runCheck" :disabled="loading">一致性检查</button>
              <button class="btn-primary" @click="submitForApproval" :disabled="loading || !detail.entities.length">提交审批</button>
              <button class="btn-danger-outline" @click="deleteVersion">删除草稿</button>
            </template>
            <template v-else-if="detail.status === 'pending_approval'">
              <button class="btn-primary" @click="approveVersion" :disabled="loading">审批通过</button>
              <button class="btn-danger-outline" @click="showRejectDialog = true">驳回</button>
            </template>
            <template v-else-if="detail.status === 'published'">
              <button class="btn-secondary" @click="rollbackVersion" :disabled="loading">回滚到此版本</button>
            </template>
            <button
              v-if="detail.status === 'draft' || detail.status === 'pending_approval'"
              class="btn-outline"
              @click="previewImpact"
            >
              预览影响
            </button>
          </div>
        </template>
        <div v-else class="version-empty-main">
          <p>选择左侧版本查看详情，或创建新版本</p>
        </div>
      </div>
    </div>

    <!-- 创建版本弹窗 -->
    <div v-if="showCreateDialog" class="modal-overlay" @click.self="showCreateDialog = false">
      <div class="modal-box">
        <h3>创建新版本</h3>
        <div class="form-group">
          <label>版本名称</label>
          <input v-model="newVersion.name" placeholder="例如：携号转网实体集" />
        </div>
        <div class="form-group">
          <label>描述（可选）</label>
          <textarea v-model="newVersion.description" rows="3" placeholder="本次发布的说明"></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreateDialog = false">取消</button>
          <button class="btn-primary" @click="createVersion" :disabled="!newVersion.name.trim()">创建</button>
        </div>
      </div>
    </div>

    <!-- 实体选择弹窗 -->
    <div v-if="showEntitySelector" class="modal-overlay" @click.self="showEntitySelector = false">
      <div class="modal-box modal-box--wide">
        <h3>选择实体</h3>
        <div class="selector-list">
          <label v-for="e in availableEntities" :key="e.id" class="selector-item">
            <input type="checkbox" v-model="selectedEntityIds" :value="e.id" />
            <span class="selector-item__name">{{ e.name_cn }}</span>
            <span class="selector-item__en">{{ e.name }}</span>
            <span class="selector-item__tier">T{{ e.tier }}</span>
          </label>
          <div v-if="!availableEntities.length" class="entity-empty">所有实体已添加</div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showEntitySelector = false">取消</button>
          <button class="btn-primary" @click="addEntities" :disabled="!selectedEntityIds.length">添加选中 ({{ selectedEntityIds.length }})</button>
        </div>
      </div>
    </div>

    <!-- 驳回弹窗 -->
    <div v-if="showRejectDialog" class="modal-overlay" @click.self="showRejectDialog = false">
      <div class="modal-box">
        <h3>驳回版本</h3>
        <div class="form-group">
          <label>驳回原因</label>
          <textarea v-model="rejectReason" rows="3" placeholder="请填写驳回原因"></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showRejectDialog = false">取消</button>
          <button class="btn-danger" @click="rejectVersion" :disabled="!rejectReason.trim()">确认驳回</button>
        </div>
      </div>
    </div>

    <!-- Impact Preview -->
    <div v-if="showImpact" class="impact-overlay">
      <div class="impact-dialog">
        <div class="impact-dialog__header">
          <h3>发布影响预览</h3>
          <button class="impact-dialog__close" @click="showImpact = false">&times;</button>
        </div>
        <div class="impact-dialog__body">
          <div v-if="impactLoading" class="impact-dialog__loading">分析中...</div>
          <div v-else-if="!impactData?.breaking_changes?.length" class="impact-dialog__empty">
            无破坏性变更，可安全发布
          </div>
          <template v-else>
            <h4>破坏性变更 ({{ impactData.breaking_changes.length }})</h4>
            <ul class="impact-dialog__list">
              <li v-for="c in impactData.breaking_changes" :key="c.entity_name">
                <strong>{{ c.entity_name }}</strong> —
                <span v-if="c.change_type === 'deleted'" class="impact-dialog__tag--del">已删除</span>
                <span v-else class="impact-dialog__tag--ren">改名为 {{ c.new_name }}</span>
              </li>
            </ul>
            <h4 v-if="impactData.affected_scenes?.length">受影响的场景 ({{ impactData.affected_scenes.length }})</h4>
            <ul v-if="impactData.affected_scenes?.length" class="impact-dialog__list">
              <li v-for="s in impactData.affected_scenes" :key="s.id">{{ s.name }}</li>
            </ul>
            <h4 v-if="impactData.affected_agents?.length">受影响的 Agent ({{ impactData.affected_agents.length }})</h4>
            <ul v-if="impactData.affected_agents?.length" class="impact-dialog__list">
              <li v-for="a in impactData.affected_agents" :key="a.id">{{ a.name }}</li>
            </ul>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { get, post, put, del } from '../../api/client'
import { ontologyPublishApi } from '../../api/aip'

interface VersionSummary {
  id: string; version_number: number; name: string; description: string | null
  status: string; entity_count: number; created_by: string | null
  created_at: string | null; submitted_at: string | null; published_at: string | null
  is_active: boolean; rollback_from: number | null
}

interface Readiness { has_datasource: boolean; mapped_attrs: number; total_attrs: number; mapping_ratio: number; issues: string[]; ready: boolean }

interface VersionEntity {
  id: string; source_entity_id: string; name: string; name_cn: string
  tier: number; description: string | null; attribute_count: number; mapped_count: number
  readiness: Readiness
}

interface VersionDetail extends VersionSummary {
  rejected_at: string | null; reject_reason: string | null; approved_by: string | null
  entities: VersionEntity[]; relations: any[]
}

interface CheckResult { passed: boolean; entity_issues: any[]; relation_issues: any[]; summary: string }
interface EntityItem { id: string; name: string; name_cn: string; tier: number }

const versions = ref<VersionSummary[]>([])
const selectedVersionId = ref<string | null>(null)
const detail = ref<VersionDetail | null>(null)
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

const availableEntities = computed(() => {
  if (!detail.value) return allEntities.value
  const inVersion = new Set(detail.value.entities.map(e => e.source_entity_id))
  return allEntities.value.filter(e => !inVersion.has(e.id))
})

onMounted(async () => {
  await loadVersions()
  await loadAllEntities()
})

async function loadVersions() {
  versions.value = await get('/ontology-publish/versions')
}

async function loadAllEntities() {
  const list = await get('/entities')
  allEntities.value = (list.items || list).map((e: any) => ({ id: e.id, name: e.name, name_cn: e.name_cn, tier: e.tier }))
}

async function selectVersion(id: string) {
  selectedVersionId.value = id
  checkResult.value = null
  detail.value = await get(`/ontology-publish/versions/${id}`)
}

async function createVersion() {
  const v = await post('/ontology-publish/versions', { name: newVersion.name, description: newVersion.description || null })
  showCreateDialog.value = false
  newVersion.name = ''
  newVersion.description = ''
  await loadVersions()
  await selectVersion(v.id)
}

async function deleteVersion() {
  if (!detail.value) return
  await del(`/ontology-publish/versions/${detail.value.id}`)
  detail.value = null
  selectedVersionId.value = null
  await loadVersions()
}

async function addEntities() {
  if (!detail.value) return
  loading.value = true
  await post(`/ontology-publish/versions/${detail.value.id}/entities`, { entity_ids: selectedEntityIds.value })
  selectedEntityIds.value = []
  showEntitySelector.value = false
  await selectVersion(detail.value.id)
  await loadVersions()
  loading.value = false
}

async function removeEntity(entityId: string) {
  if (!detail.value) return
  await del(`/ontology-publish/versions/${detail.value.id}/entities/${entityId}`)
  await selectVersion(detail.value.id)
  await loadVersions()
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
    await loadVersions()
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
  await loadVersions()
  await selectVersion(detail.value.id)
  loading.value = false
}

async function rejectVersion() {
  if (!detail.value) return
  await post(`/ontology-publish/versions/${detail.value.id}/reject`, { reason: rejectReason.value })
  rejectReason.value = ''
  showRejectDialog.value = false
  await loadVersions()
  await selectVersion(detail.value.id)
}

async function rollbackVersion() {
  if (!detail.value) return
  loading.value = true
  const v = await post(`/ontology-publish/versions/${detail.value.id}/rollback`)
  await loadVersions()
  await selectVersion(v.id)
  loading.value = false
}

async function previewImpact() {
  if (!detail.value) return
  showImpact.value = true
  impactLoading.value = true
  try {
    const res = await ontologyPublishApi.previewImpact(detail.value.id)
    impactData.value = res
  } catch (e) {
    impactData.value = null
  } finally {
    impactLoading.value = false
  }
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
.page-title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 4px 0 0; }
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
.meta-card__rollback { margin-top: 6px; font-size: 11px; color: var(--neutral-500); font-style: italic; }

.status-tag { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.status-tag--draft { background: #e0e7ff; color: #3730a3; }
.status-tag--pending_approval { background: #fef3c7; color: #92400e; }
.status-tag--published { background: #dcfce7; color: #166534; }
.status-tag--rejected { background: #fee2e2; color: #991b1b; }

.entity-card { background: #fff; border: 1px solid var(--neutral-100); border-radius: 10px; padding: 16px; }
.entity-card__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.entity-card__header h3 { font-size: 14px; font-weight: 600; margin: 0; }
.entity-table__row { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--neutral-50); font-size: 13px; }
.entity-table__row--header { font-size: 11px; font-weight: 600; color: var(--neutral-500); text-transform: uppercase; }
.col-name { flex: 2; display: flex; flex-direction: column; gap: 1px; }
.col-name small { font-size: 11px; color: var(--neutral-400); }
.col-tier { width: 50px; text-align: center; }
.col-attrs { width: 70px; text-align: center; }
.col-status { width: 50px; text-align: center; }
.col-action { width: 60px; text-align: center; }
.check-pass { color: #16a34a; font-weight: 700; }
.check-fail { color: #dc2626; font-weight: 700; }
.entity-empty { font-size: 13px; color: var(--neutral-400); text-align: center; padding: 20px; }

.check-card { background: #fff; border: 1px solid var(--neutral-100); border-radius: 10px; padding: 16px; }
.check-card h3 { font-size: 14px; font-weight: 600; margin: 0 0 10px; }
.check-card__summary { font-size: 13px; font-weight: 600; padding: 8px 12px; border-radius: 6px; }
.check-card__summary--pass { background: #dcfce7; color: #166534; }
.check-card__summary--fail { background: #fef2f2; color: #dc2626; }
.check-card__issues { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.issue-item { font-size: 12px; color: #dc2626; padding: 4px 8px; background: #fef2f2; border-radius: 4px; }
.issue-item--rel { color: #92400e; background: #fef3c7; }

.action-bar { display: flex; gap: 10px; align-items: center; padding-top: 8px; }

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

.btn-outline { padding: 8px 18px; border-radius: 6px; border: 1px solid var(--neutral-300); background: #fff; color: var(--neutral-700); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-outline:hover { background: var(--neutral-50); }

.impact-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.impact-dialog {
  background: #fff;
  border-radius: 8px;
  width: 480px;
  max-height: 70vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}
.impact-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
}
.impact-dialog__header h3 { margin: 0; font-size: 16px; }
.impact-dialog__close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #6b7280;
}
.impact-dialog__body { padding: 16px 20px; }
.impact-dialog__body h4 { margin: 12px 0 6px; font-size: 13px; color: #374151; }
.impact-dialog__list { margin: 0; padding-left: 16px; font-size: 13px; }
.impact-dialog__list li { margin: 4px 0; }
.impact-dialog__loading { text-align: center; color: #6b7280; padding: 20px; }
.impact-dialog__empty { text-align: center; color: #059669; padding: 20px; }
.impact-dialog__tag--del { color: #dc2626; }
.impact-dialog__tag--ren { color: #d97706; }
</style>
