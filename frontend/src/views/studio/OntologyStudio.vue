<template>
  <div class="studio" :class="{ 'studio--fullscreen': fullscreen }">
    <!-- 左栏：搜索 + 按 tier 分组的对象列表 -->
    <aside class="studio__sider" v-show="!fullscreen">
      <div class="studio__search">
        <input v-model="searchText" placeholder="搜索对象类型..." class="studio__search-input" />
      </div>

      <div class="studio__tier-group" v-for="tier in [1, 2, 3] as const" :key="tier">
        <div class="studio__tier-header">
          <span class="studio__tier-dot" :style="{ background: tierColor[tier] }"></span>
          <span class="studio__tier-name">{{ tierName[tier] }}</span>
          <span class="studio__tier-count">{{ filteredByTier(tier).length }}</span>
        </div>
        <div
          v-for="obj in filteredByTier(tier)"
          :key="obj.apiName"
          class="studio__obj-item"
          :class="{ 'studio__obj-item--active': selectedObject?.apiName === obj.apiName }"
          :style="{ borderLeftColor: selectedObject?.apiName === obj.apiName ? tierColor[tier] : 'transparent' }"
          @click="selectObject(obj)"
        >
          <div class="studio__obj-info">
            <div class="studio__obj-cn">{{ obj.displayName }}</div>
            <div class="studio__obj-en">{{ obj.apiName }}</div>
          </div>
          <span class="studio__obj-badge">{{ obj.aboxScale > 0 ? formatNumber(obj.aboxScale) : '—' }}</span>
        </div>
      </div>

      <!-- 本体统计 -->
      <div class="studio__stats">
        <div class="studio__stats-title">本体统计</div>
        <div class="studio__stats-grid">
          <div><span class="studio__stats-label">总类数:</span> <strong>{{ tbox?.meta.objectTypeCount ?? 0 }}</strong></div>
          <div><span class="studio__stats-label">关系数:</span> <strong>{{ tbox?.meta.linkTypeCount ?? 0 }}</strong></div>
          <div><span class="studio__stats-label">属性数:</span> <strong>{{ tbox?.meta.propertyCount ?? 0 }}</strong></div>
          <div><span class="studio__stats-label">规则数:</span> <strong>{{ stats?.rbox.ruleCount ?? 0 }}</strong></div>
        </div>
      </div>
    </aside>

    <!-- 主体：视图切换器 + 视图内容 -->
    <main class="studio__main">
      <header class="studio__header">
        <div class="studio__header-info">
          <strong>{{ tbox?.meta.objectTypeCount ?? 0 }} 个对象类型 · {{ tbox?.meta.linkTypeCount ?? 0 }} 条关系</strong>
          <span class="studio__owl-tag">W3C OWL</span>
          <span v-if="stats" class="studio__abox-tag">{{ formatNumber(stats.abox.individualCount) }} 个实例</span>
        </div>
        <div class="studio__view-switcher">
          <button
            v-for="v in viewOptions"
            :key="v.value"
            class="studio__view-btn"
            :class="{ 'studio__view-btn--active': activeView === v.value }"
            @click="activeView = v.value"
          >
            {{ v.label }}
          </button>
        </div>
        <button class="studio__refresh-btn" @click="refreshCounts" :disabled="refreshing" :title="lastRefreshAt ? '上次刷新: ' + lastRefreshAt : '刷新数据源实例数'">
          <span v-if="refreshing">⟳ 刷新中</span>
          <span v-else>⟳ 刷新数据</span>
        </button>
        <button
          v-if="canFullscreen"
          class="studio__fullscreen-btn"
          @click="fullscreen = !fullscreen"
          :title="fullscreen ? '退出全屏' : '进入全屏'"
        >
          {{ fullscreen ? '✕ 退出全屏' : '⛶ 全屏' }}
        </button>
      </header>

      <div class="studio__body" v-if="!loading && tbox">
        <StudioCardView
          v-if="activeView === 'card'"
          :objects="tbox.objectTypes"
          :relations="tbox.linkTypes"
          :hydration="aboxHydrationMap"
          @select="selectObject"
        />
        <StudioThreeBox
          v-else-if="activeView === 'threebox'"
          :objects="tbox.objectTypes"
          :relations="tbox.linkTypes"
          :rules="rbox?.rules ?? []"
          :hydration="aboxHydrationMap"
          @select="selectObject"
        />
        <StudioBusinessView
          v-else-if="activeView === 'business'"
          :objects="tbox.objectTypes"
          :relations="tbox.linkTypes"
          :selected="selectedObject"
          @select="selectObject"
        />
        <StudioTwinView
          v-else-if="activeView === 'twin'"
          :objects="tbox.objectTypes"
          :relations="tbox.linkTypes"
          :selected="selectedObject"
          @select="selectObject"
        />
        <StudioSemanticView
          v-else-if="activeView === 'flow'"
          :objects="tbox.objectTypes"
          :relations="tbox.linkTypes"
          :selected="selectedObject"
          @select="selectObject"
        />
        <div v-else class="studio__placeholder">
          <p>未知视图</p>
        </div>
      </div>

      <div v-else class="studio__loading">加载本体数据...</div>
    </main>

    <!-- 右栏：详情面板（选中对象时显示）-->
    <aside v-if="selectedObject && !fullscreen" class="studio__detail">
      <div class="studio__detail-header">
        <div class="studio__detail-icon" :style="{ background: tierColor[selectedObject.tier] + '20', color: tierColor[selectedObject.tier] }">
          {{ selectedObject.displayName.charAt(0) }}
        </div>
        <div>
          <div class="studio__detail-name">{{ selectedObject.displayName }}</div>
          <div class="studio__detail-en">{{ selectedObject.apiName }} · T{{ selectedObject.tier }} {{ tierName[selectedObject.tier] }}</div>
        </div>
        <button class="studio__detail-close" @click="selectedObject = null">×</button>
      </div>

      <div class="studio__detail-meta">
        <p v-if="selectedObject.description" class="studio__detail-desc">{{ selectedObject.description }}</p>
        <div class="studio__detail-actions">
          <button class="studio__detail-link" @click="narratorVisible = true">
            <span style="color:#f59e0b">⚡</span> AI 解读
          </button>
          <button class="studio__detail-link" @click="openInDetail">在实体详情中打开 →</button>
        </div>
      </div>

      <div class="studio__detail-tabs">
        <button
          v-for="t in detailTabs"
          :key="t.value"
          class="studio__detail-tab"
          :class="{ 'studio__detail-tab--active': activeDetailTab === t.value }"
          @click="activeDetailTab = t.value"
        >
          {{ t.label }} <span class="studio__detail-tab-count">{{ tabCount(t.value) }}</span>
        </button>
      </div>

      <div class="studio__detail-body">
        <!-- 属性 -->
        <template v-if="activeDetailTab === 'attributes'">
          <div v-if="selectedObject.properties.length === 0" class="studio__detail-empty">暂无属性</div>
          <div v-for="p in selectedObject.properties" :key="p.apiName" class="studio__detail-row">
            <div class="studio__detail-row-main">
              <span class="studio__detail-row-name">{{ p.displayName }}</span>
              <span class="studio__detail-row-tag">{{ p.dataType }}</span>
              <span v-if="p.required" class="studio__detail-row-required">必填</span>
            </div>
            <div v-if="p.sourceTable" class="studio__detail-row-sub">
              <code>{{ p.sourceTable }}.{{ p.sourceColumn || '?' }}</code>
            </div>
            <div v-else class="studio__detail-row-sub studio__detail-row-sub--muted">未映射</div>
          </div>
        </template>

        <!-- 关系 -->
        <template v-else-if="activeDetailTab === 'relations'">
          <div v-if="relatedLinks.length === 0" class="studio__detail-empty">暂无关系</div>
          <div v-for="r in relatedLinks" :key="r.apiName + r.source + r.target" class="studio__detail-row">
            <div class="studio__detail-row-main">
              <span class="studio__detail-row-arrow">{{ r.source === selectedObject.apiName ? '→' : '←' }}</span>
              <span class="studio__detail-row-name">{{ r.displayName }}</span>
              <span class="studio__detail-row-tag studio__detail-row-tag--blue">{{ r.cardinality }}</span>
            </div>
            <div class="studio__detail-row-sub">
              <code>{{ r.source === selectedObject.apiName ? r.target : r.source }}</code>
            </div>
          </div>
        </template>

        <!-- 规则 -->
        <template v-else-if="activeDetailTab === 'rules'">
          <div v-if="detailLoading" class="studio__detail-empty">加载中...</div>
          <div v-else-if="entityDetail?.rules?.length === 0" class="studio__detail-empty">暂无规则</div>
          <div v-for="r in entityDetail?.rules ?? []" :key="r.id" class="studio__detail-row">
            <div class="studio__detail-row-main">
              <span class="studio__detail-row-name">{{ r.name }}</span>
              <span class="studio__detail-row-tag studio__detail-row-tag--orange">P{{ r.priority || 5 }}</span>
            </div>
            <div class="studio__detail-row-sub">{{ r.action_desc || r.condition_expr }}</div>
          </div>
        </template>

        <!-- 动作 -->
        <template v-else-if="activeDetailTab === 'actions'">
          <div v-if="detailLoading" class="studio__detail-empty">加载中...</div>
          <div v-else-if="entityDetail?.actions?.length === 0" class="studio__detail-empty">暂无动作</div>
          <div v-for="a in entityDetail?.actions ?? []" :key="a.id" class="studio__detail-row">
            <div class="studio__detail-row-main">
              <span class="studio__detail-row-name">{{ a.name }}</span>
              <span class="studio__detail-row-tag studio__detail-row-tag--purple">{{ a.type }}</span>
            </div>
            <div v-if="a.impact_count" class="studio__detail-row-sub">影响 {{ a.impact_count }} 实体</div>
          </div>
        </template>

        <!-- 函数 -->
        <template v-else-if="activeDetailTab === 'functions'">
          <div v-if="detailLoading" class="studio__detail-empty">加载中...</div>
          <div v-else-if="entityDetail?.functions?.length === 0" class="studio__detail-empty">暂无函数</div>
          <div v-for="f in entityDetail?.functions ?? []" :key="f.id" class="studio__detail-row">
            <div class="studio__detail-row-main">
              <span class="studio__detail-row-name">{{ f.name }}</span>
              <span class="studio__detail-row-tag studio__detail-row-tag--blue">
                函数
              </span>
            </div>
            <div v-if="f.description" class="studio__detail-row-sub">{{ f.description }}</div>
          </div>
        </template>
      </div>
    </aside>

    <OntologyNarrator
      :visible="narratorVisible"
      :obj="selectedObject"
      :rel-count="narratorRelCount"
      @close="narratorVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { studioApi, type StudioTBox, type StudioABox, type StudioRBox, type StudioStats, type StudioObjectType, type StudioHydration } from '../../api/studio'
import { entityApi } from '../../api/ontology'
import type { OntologyEntity } from '../../types/ontology'
import StudioCardView from './StudioCardView.vue'
import StudioThreeBox from './StudioThreeBox.vue'
import StudioBusinessView from './StudioBusinessView.vue'
import StudioTwinView from './StudioTwinView.vue'
import StudioSemanticView from './StudioSemanticView.vue'
import OntologyNarrator from './OntologyNarrator.vue'

const router = useRouter()

const tbox = ref<StudioTBox | null>(null)
const abox = ref<StudioABox | null>(null)
const rbox = ref<StudioRBox | null>(null)
const stats = ref<StudioStats | null>(null)
const loading = ref(true)

const activeView = ref<'card' | 'threebox' | 'business' | 'twin' | 'flow'>('card')
const selectedObject = ref<StudioObjectType | null>(null)
const searchText = ref('')
const fullscreen = ref(false)

const canFullscreen = computed(() => ['business', 'twin', 'flow'].includes(activeView.value))

watch(activeView, (v) => {
  if (!['business', 'twin', 'flow'].includes(v)) fullscreen.value = false
})

const viewOptions = [
  { value: 'card' as const, label: '卡片视图' },
  { value: 'threebox' as const, label: '三盒架构' },
  { value: 'business' as const, label: '业务视图' },
  { value: 'twin' as const, label: '数字孪生' },
  { value: 'flow' as const, label: '语义网络' },
]

const tierColor: Record<1 | 2 | 3, string> = { 1: '#2E5BFF', 2: '#00C7B1', 3: '#FF6B35' }
const tierName: Record<1 | 2 | 3, string> = { 1: '核心', 2: '领域', 3: '场景' }

const aboxHydrationMap = computed(() => {
  const m: Record<string, StudioHydration> = {}
  for (const h of abox.value?.hydration ?? []) m[h.objectTypeApiName] = h
  return m
})

function filteredByTier(tier: 1 | 2 | 3) {
  const q = searchText.value.trim().toLowerCase()
  return (tbox.value?.objectTypes ?? [])
    .filter(o => o.tier === tier)
    .filter(o => !q || o.apiName.toLowerCase().includes(q) || o.displayName.toLowerCase().includes(q))
}

function selectObject(o: StudioObjectType | null) {
  selectedObject.value = o
  if (!o) return
  // 切换对象时若 tab 是规则/动作/函数，触发详情懒加载
  if (['rules', 'actions', 'functions'].includes(activeDetailTab.value)) {
    loadEntityDetail(o.id)
  }
}

// 详情面板 tab
type DetailTab = 'attributes' | 'relations' | 'rules' | 'actions' | 'functions'
const detailTabs: { value: DetailTab; label: string }[] = [
  { value: 'attributes', label: '属性' },
  { value: 'relations', label: '关系' },
  { value: 'rules', label: '规则' },
  { value: 'actions', label: '动作' },
  { value: 'functions', label: '函数' },
]
const activeDetailTab = ref<DetailTab>('attributes')
const entityDetail = ref<OntologyEntity | null>(null)
const detailLoading = ref(false)

function tabCount(tab: DetailTab): number {
  if (!selectedObject.value) return 0
  switch (tab) {
    case 'attributes': return selectedObject.value.properties.length
    case 'relations': return relatedLinks.value.length
    case 'rules': return selectedObject.value.ruleCount
    case 'actions': return selectedObject.value.actionCount
    case 'functions': return selectedObject.value.functionCount
  }
}

const relatedLinks = computed(() => {
  if (!selectedObject.value || !tbox.value) return []
  const name = selectedObject.value.apiName
  return tbox.value.linkTypes.filter(l => l.source === name || l.target === name)
})

async function loadEntityDetail(entityId: string) {
  if (entityDetail.value?.id === entityId) return
  detailLoading.value = true
  try {
    entityDetail.value = await entityApi.detail(entityId)
  } catch (e) {
    console.error('加载实体详情失败', e)
  } finally {
    detailLoading.value = false
  }
}

watch(activeDetailTab, (tab) => {
  if (selectedObject.value && ['rules', 'actions', 'functions'].includes(tab)) {
    loadEntityDetail(selectedObject.value.id)
  }
})

function openInDetail() {
  if (selectedObject.value) router.push(`/ontology/${selectedObject.value.id}`)
}

const narratorVisible = ref(false)
const narratorRelCount = computed(() => {
  if (!selectedObject.value || !tbox.value) return 0
  const name = selectedObject.value.apiName
  return tbox.value.linkTypes.filter(l => l.source === name || l.target === name).length
})

function formatNumber(n: number) {
  return n.toLocaleString('en-US')
}

const refreshing = ref(false)
const lastRefreshAt = ref<string | null>(null)

async function refreshCounts() {
  refreshing.value = true
  try {
    await studioApi.refreshCounts()
    lastRefreshAt.value = new Date().toLocaleTimeString('zh-CN')
    // 重新拉取所有数据
    await reload()
  } catch (e) {
    console.error('刷新失败', e)
  } finally {
    refreshing.value = false
  }
}

async function reload() {
  const [t, a, r, s] = await Promise.all([
    studioApi.tbox(),
    studioApi.abox(),
    studioApi.rbox(),
    studioApi.stats(),
  ])
  tbox.value = t
  abox.value = a
  rbox.value = r
  stats.value = s
}

onMounted(async () => {
  try {
    await reload()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.studio {
  display: flex;
  height: 100%;
  background: #f8fafc;
}
.studio--fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

/* 左栏 */
.studio__sider {
  width: 260px;
  min-width: 200px;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.studio__search {
  padding: 12px 12px 8px;
  border-bottom: 1px solid #f1f5f9;
}
.studio__search-input {
  width: 100%;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  outline: none;
}
.studio__search-input:focus { border-color: #4f6ef7; }

.studio__tier-group {
  margin-top: 8px;
  max-height: 280px;
  overflow-y: auto;
}
.studio__tier-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px 4px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.studio__tier-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.studio__tier-count {
  background: #e2e8f0;
  color: #64748b;
  padding: 0 6px;
  font-size: 10px;
  border-radius: 8px;
  font-weight: 600;
  margin-left: auto;
}
.studio__obj-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  cursor: pointer;
  border-left: 3px solid transparent;
  font-size: 12px;
  transition: background 0.1s;
}
.studio__obj-item:hover { background: #f8fafc; }
.studio__obj-item--active { background: #eff6ff; font-weight: 600; }
.studio__obj-info { flex: 1; min-width: 0; }
.studio__obj-cn { font-size: 13px; color: #1e293b; line-height: 1.3; }
.studio__obj-en { font-size: 10px; color: #94a3b8; font-family: monospace; line-height: 1.3; }
.studio__obj-badge {
  font-size: 10px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.studio__stats {
  margin-top: auto;
  padding: 12px 16px;
  background: #f8fafc;
  border-top: 1px solid #e5e7eb;
}
.studio__stats-title {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
}
.studio__stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 12px;
  font-size: 12px;
}
.studio__stats-label { color: #94a3b8; font-size: 11px; }

/* 主体 */
.studio__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.studio__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}
.studio__header-info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #1e293b;
}
.studio__owl-tag {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 4px;
  font-weight: 500;
}
.studio__abox-tag {
  background: #ecfdf5;
  color: #047857;
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 4px;
  font-weight: 500;
}
.studio__refresh-btn {
  margin-left: 12px;
  padding: 5px 12px;
  font-size: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
}
.studio__refresh-btn:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #94a3b8;
}
.studio__refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.studio__view-switcher {
  display: inline-flex;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}
.studio__view-btn {
  padding: 4px 12px;
  font-size: 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #475569;
  transition: all 0.15s;
}
.studio__view-btn:hover { background: rgba(255,255,255,0.5); }
.studio__view-btn--active {
  background: #fff;
  color: #1e293b;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.studio__body {
  flex: 1;
  overflow: auto;
  padding: 16px 20px;
}
.studio__loading, .studio__placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 13px;
}

/* 右栏 */
.studio__detail {
  width: 320px;
  min-width: 280px;
  background: #fff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.studio__detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  position: relative;
}
.studio__detail-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
}
.studio__detail-name { font-size: 15px; font-weight: 700; color: #1e293b; }
.studio__detail-en { font-size: 11px; color: #94a3b8; font-family: monospace; }
.studio__detail-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  color: #94a3b8;
  border-radius: 4px;
}
.studio__detail-close:hover { background: #f1f5f9; color: #1e293b; }

.studio__detail-meta {
  padding: 12px 20px;
  border-bottom: 1px solid #f1f5f9;
}
.studio__detail-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 8px;
}
.studio__detail-link {
  font-size: 11px;
  background: transparent;
  border: 1px solid #e5e7eb;
  color: #4f6ef7;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}
.studio__detail-link:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.studio__detail-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* 详情 tab */
.studio__detail-tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  background: #fafbfc;
  padding: 0 12px;
  overflow-x: auto;
}
.studio__detail-tab {
  position: relative;
  padding: 10px 12px;
  font-size: 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #64748b;
  font-weight: 500;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
}
.studio__detail-tab:hover { color: #1e293b; }
.studio__detail-tab--active {
  color: #4f6ef7;
  border-bottom-color: #4f6ef7;
  font-weight: 600;
}
.studio__detail-tab-count {
  display: inline-block;
  margin-left: 4px;
  font-size: 10px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 500;
}
.studio__detail-tab--active .studio__detail-tab-count {
  background: #dbeafe;
  color: #1d4ed8;
}

/* 详情正文 */
.studio__detail-body {
  padding: 12px 16px;
  flex: 1;
  overflow-y: auto;
}
.studio__detail-empty {
  text-align: center;
  padding: 24px 0;
  color: #94a3b8;
  font-size: 12px;
}
.studio__detail-row {
  padding: 8px 10px;
  margin-bottom: 4px;
  background: #fafbfc;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
  transition: background 0.1s;
}
.studio__detail-row:hover {
  background: #f0f7ff;
  border-color: #bfdbfe;
}
.studio__detail-row-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.studio__detail-row-name {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  min-width: 0;
}
.studio__detail-row-arrow {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 700;
}
.studio__detail-row-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #e2e8f0;
  color: #475569;
  font-weight: 500;
}
.studio__detail-row-tag--blue { background: #dbeafe; color: #1d4ed8; }
.studio__detail-row-tag--orange { background: #fed7aa; color: #c2410c; }
.studio__detail-row-tag--purple { background: #ede9fe; color: #6d28d9; }
.studio__detail-row-tag--green { background: #d1fae5; color: #047857; }
.studio__detail-row-required {
  font-size: 10px;
  background: #fef3c7;
  color: #92400e;
  padding: 1px 6px;
  border-radius: 3px;
}
.studio__detail-row-sub {
  margin-top: 4px;
  font-size: 11px;
  color: #64748b;
  line-height: 1.4;
}
.studio__detail-row-sub--muted { color: #cbd5e1; font-style: italic; }
.studio__detail-row-sub code {
  font-family: monospace;
  font-size: 10px;
  background: #fff;
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid #e5e7eb;
}
</style>
