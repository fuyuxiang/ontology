<template>
  <div class="publish-page">
    <div class="publish-page__header">
      <h1 class="page-title">本体发布</h1>
      <p class="page-desc">将本体实体封装为可消费的服务，发布后可被 API 服务、OSDK、Agent 和流程编排使用</p>
    </div>

    <div class="publish-page__body">
      <!-- 左侧：实体列表 -->
      <div class="publish-sidebar">
        <div class="publish-sidebar__stats">
          <span class="stat-item"><strong>{{ publishedCount }}</strong> 已发布</span>
          <span class="stat-item"><strong>{{ readyCount }}</strong> 就绪</span>
          <span class="stat-item"><strong>{{ notReadyCount }}</strong> 未就绪</span>
        </div>
        <div class="publish-sidebar__list">
          <div
            v-for="item in entityList"
            :key="item.id"
            class="entity-row"
            :class="{ 'entity-row--active': selectedId === item.id }"
            @click="selectEntity(item)"
          >
            <span class="entity-row__status" :class="`entity-row__status--${item.status}`"></span>
            <div class="entity-row__info">
              <span class="entity-row__name">{{ item.name_cn }}</span>
              <span class="entity-row__en">{{ item.name }}</span>
            </div>
            <span class="entity-row__badge" :class="`entity-row__badge--${getStatusLabel(item).key}`">{{ getStatusLabel(item).text }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧：发布配置 -->
      <div class="publish-main">
        <template v-if="selected">
          <!-- 就绪检查 -->
          <div class="check-card">
            <h3 class="section-title">就绪检查</h3>
            <div class="check-items">
              <div class="check-item" :class="selected.readiness.has_datasource ? 'check-item--pass' : 'check-item--fail'">
                <span class="check-icon">{{ selected.readiness.has_datasource ? '✓' : '✗' }}</span>
                <span>数据源绑定</span>
              </div>
              <div class="check-item" :class="selected.readiness.total_attrs > 0 ? 'check-item--pass' : 'check-item--fail'">
                <span class="check-icon">{{ selected.readiness.total_attrs > 0 ? '✓' : '✗' }}</span>
                <span>属性定义 ({{ selected.readiness.total_attrs }} 个)</span>
              </div>
              <div class="check-item" :class="selected.readiness.mapping_ratio >= 0.5 ? 'check-item--pass' : 'check-item--fail'">
                <span class="check-icon">{{ selected.readiness.mapping_ratio >= 0.5 ? '✓' : '✗' }}</span>
                <span>字段映射 ({{ selected.readiness.mapped_attrs }}/{{ selected.readiness.total_attrs }}, {{ Math.round(selected.readiness.mapping_ratio * 100) }}%)</span>
              </div>
              <div class="check-item" :class="selected.readiness.has_relations ? 'check-item--pass' : 'check-item--warn'">
                <span class="check-icon">{{ selected.readiness.has_relations ? '✓' : '⚠' }}</span>
                <span>关系定义 {{ selected.readiness.has_relations ? '' : '(可选)' }}</span>
              </div>
            </div>
            <div v-if="selected.readiness.issues.length" class="check-issues">
              <div v-for="issue in selected.readiness.issues" :key="issue" class="check-issue">{{ issue }}</div>
            </div>
          </div>

          <!-- 能力配置 -->
          <div class="config-card">
            <h3 class="section-title">能力配置</h3>
            <div class="capability-list">
              <label class="cap-item" v-for="cap in capabilities" :key="cap.key">
                <input type="checkbox" v-model="publishConfig.capabilities" :value="cap.key" />
                <span class="cap-item__label">{{ cap.label }}</span>
                <span class="cap-item__desc">{{ cap.desc }}</span>
              </label>
            </div>

            <div class="config-row">
              <label class="config-label">访问级别</label>
              <select v-model="publishConfig.access_level" class="config-select">
                <option value="public">公开（无需认证）</option>
                <option value="api_key">API Key 认证</option>
                <option value="token">Token 认证</option>
              </select>
            </div>
          </div>

          <!-- 预览 -->
          <div class="preview-card" v-if="selected.readiness.ready">
            <h3 class="section-title">发布后将生成</h3>
            <div class="preview-endpoints">
              <div v-for="ep in previewEndpoints" :key="ep" class="preview-ep">
                <span class="preview-ep__method">{{ ep.method }}</span>
                <code>{{ ep.path }}</code>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="publish-actions">
            <template v-if="selected.status === 'published'">
              <button class="btn-danger" @click="unpublish">取消发布</button>
              <span class="publish-hint">已发布，可被本体服务消费</span>
            </template>
            <template v-else>
              <button class="btn-primary" @click="publish" :disabled="!selected.readiness.ready || publishing">
                {{ publishing ? '发布中...' : '确认发布' }}
              </button>
              <span v-if="!selected.readiness.ready" class="publish-hint publish-hint--warn">请先完成就绪检查中的必要项</span>
            </template>
          </div>
        </template>
        <div v-else class="publish-empty">
          <p>选择左侧实体查看发布状态</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { get, post } from '../../api/client'

interface Readiness { has_datasource: boolean; mapped_attrs: number; total_attrs: number; mapping_ratio: number; has_relations: boolean; issues: string[]; ready: boolean }
interface EntityStatus { id: string; name: string; name_cn: string; tier: number; status: string; publish_config: any; readiness: Readiness }

const entityList = ref<EntityStatus[]>([])
const selectedId = ref<string | null>(null)
const publishing = ref(false)

const publishConfig = reactive({ capabilities: ['query', 'relations'] as string[], access_level: 'api_key' })

const capabilities = [
  { key: 'query', label: '查询', desc: '列表查询、详情获取、条件过滤' },
  { key: 'relations', label: '关系遍历', desc: '获取关联实体、多跳遍历' },
  { key: 'write', label: '写入', desc: '创建、更新实例数据' },
  { key: 'rules', label: '规则执行', desc: '执行绑定的业务规则' },
]

const selected = computed(() => entityList.value.find(e => e.id === selectedId.value) || null)
const publishedCount = computed(() => entityList.value.filter(e => e.status === 'published').length)
const readyCount = computed(() => entityList.value.filter(e => e.status !== 'published' && e.readiness.ready).length)
const notReadyCount = computed(() => entityList.value.filter(e => e.status !== 'published' && !e.readiness.ready).length)

const previewEndpoints = computed(() => {
  if (!selected.value) return []
  const name = selected.value.name
  const eps = []
  if (publishConfig.capabilities.includes('query')) {
    eps.push({ method: 'GET', path: `/ontology-api/objects/${name}` })
    eps.push({ method: 'GET', path: `/ontology-api/objects/${name}/{id}` })
  }
  if (publishConfig.capabilities.includes('relations')) {
    eps.push({ method: 'GET', path: `/ontology-api/objects/${name}/{id}/relations` })
  }
  if (publishConfig.capabilities.includes('write')) {
    eps.push({ method: 'POST', path: `/ontology-api/objects/${name}` })
  }
  if (publishConfig.capabilities.includes('rules')) {
    eps.push({ method: 'POST', path: `/ontology-api/objects/${name}/execute-rule` })
  }
  return eps
})

function getStatusLabel(item: EntityStatus) {
  if (item.status === 'published') return { key: 'published', text: '已发布' }
  if (item.readiness.ready) return { key: 'ready', text: '就绪' }
  return { key: 'notready', text: '未就绪' }
}

function selectEntity(item: EntityStatus) {
  selectedId.value = item.id
  if (item.publish_config?.capabilities) {
    publishConfig.capabilities = [...item.publish_config.capabilities]
    publishConfig.access_level = item.publish_config.access_level || 'api_key'
  } else {
    publishConfig.capabilities = ['query', 'relations']
    publishConfig.access_level = 'api_key'
  }
}

async function loadStatus() {
  try {
    const data = await get<EntityStatus[]>('/ontology-publish/status')
    entityList.value = data
  } catch { /* empty */ }
}

async function publish() {
  if (!selected.value) return
  publishing.value = true
  try {
    await post('/ontology-publish/publish', { entity_id: selected.value.id, config: publishConfig })
    await loadStatus()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '发布失败')
  } finally {
    publishing.value = false
  }
}

async function unpublish() {
  if (!selected.value || !confirm('确定取消发布？取消后本体服务将无法访问该实体。')) return
  try {
    await post(`/ontology-publish/unpublish/${selected.value.id}`, {})
    await loadStatus()
  } catch { /* ignore */ }
}

onMounted(loadStatus)
</script>

<style scoped>
.publish-page { display: flex; flex-direction: column; height: 100%; }
.publish-page__header { padding: 20px 24px 12px; flex-shrink: 0; }
.page-title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 0; }
.publish-page__body { display: flex; flex: 1; overflow: hidden; border-top: 1px solid var(--neutral-200); }

.publish-sidebar { width: 300px; flex-shrink: 0; border-right: 1px solid var(--neutral-200); display: flex; flex-direction: column; }
.publish-sidebar__stats { display: flex; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--neutral-100); }
.stat-item { font-size: 12px; color: var(--neutral-500); }
.stat-item strong { color: var(--neutral-800); }
.publish-sidebar__list { flex: 1; overflow-y: auto; padding: 8px; }

.entity-row { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 6px; cursor: pointer; }
.entity-row:hover { background: var(--neutral-50); }
.entity-row--active { background: var(--semantic-50); }
.entity-row__status { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.entity-row__status--published { background: #10b981; }
.entity-row__status--active { background: #94a3b8; }
.entity-row__info { flex: 1; min-width: 0; }
.entity-row__name { font-size: 13px; font-weight: 600; color: var(--neutral-800); display: block; }
.entity-row__en { font-size: 10px; color: var(--neutral-400); font-family: monospace; }
.entity-row__badge { font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 500; flex-shrink: 0; }
.entity-row__badge--published { background: #d1fae5; color: #059669; }
.entity-row__badge--ready { background: #dbeafe; color: #1d4ed8; }
.entity-row__badge--notready { background: var(--neutral-100); color: var(--neutral-500); }

.publish-main { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.publish-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--neutral-400); font-size: 13px; }

.section-title { font-size: 14px; font-weight: 600; color: var(--neutral-800); margin: 0 0 10px; }
.check-card, .config-card, .preview-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: 10px; padding: 16px; }

.check-items { display: flex; flex-direction: column; gap: 6px; }
.check-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--neutral-700); }
.check-item--pass .check-icon { color: #10b981; font-weight: 700; }
.check-item--fail .check-icon { color: #ef4444; font-weight: 700; }
.check-item--warn .check-icon { color: #f59e0b; font-weight: 700; }
.check-issues { margin-top: 8px; padding: 8px 10px; background: #fef2f2; border-radius: 6px; }
.check-issue { font-size: 12px; color: #dc2626; padding: 2px 0; }

.capability-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.cap-item { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; padding: 4px 0; }
.cap-item input { margin: 0; }
.cap-item__label { font-weight: 500; color: var(--neutral-800); min-width: 70px; }
.cap-item__desc { color: var(--neutral-500); font-size: 12px; }
.config-row { display: flex; align-items: center; gap: 10px; }
.config-label { font-size: 12px; font-weight: 600; color: var(--neutral-600); }
.config-select { padding: 5px 10px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 12px; }

.preview-endpoints { display: flex; flex-direction: column; gap: 4px; }
.preview-ep { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.preview-ep__method { font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px; background: #dbeafe; color: #1d4ed8; }
.preview-ep code { font-family: monospace; color: var(--neutral-700); font-size: 11px; }

.publish-actions { display: flex; align-items: center; gap: 12px; padding-top: 8px; }
.btn-primary { padding: 8px 20px; border-radius: 6px; border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { padding: 8px 20px; border-radius: 6px; border: 1px solid #fca5a5; background: #fef2f2; color: #dc2626; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-danger:hover { background: #fee2e2; }
.publish-hint { font-size: 12px; color: var(--neutral-500); }
.publish-hint--warn { color: #f59e0b; }
</style>
