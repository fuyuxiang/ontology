<template>
  <div class="studio">
    <!-- 左栏：搜索 + 按 tier 分组的对象列表 -->
    <aside class="studio__sider">
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
        <div v-else class="studio__placeholder">
          <p>{{ viewOptions.find(v => v.value === activeView)?.label }} — 视图开发中</p>
        </div>
      </div>

      <div v-else class="studio__loading">加载本体数据...</div>
    </main>

    <!-- 右栏：详情面板（选中对象时显示）-->
    <aside v-if="selectedObject" class="studio__detail">
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

      <div class="studio__detail-section">
        <p class="studio__detail-desc">{{ selectedObject.description || '暂无描述' }}</p>
        <div class="studio__detail-tags">
          <span class="studio__tag">{{ selectedObject.properties.length }} 属性</span>
          <span class="studio__tag">{{ selectedObject.ruleCount }} 规则</span>
          <span class="studio__tag">{{ selectedObject.actionCount }} 动作</span>
          <span class="studio__tag">{{ selectedObject.functionCount }} 函数</span>
        </div>
      </div>

      <div class="studio__detail-section">
        <h4>属性定义 ({{ selectedObject.properties.length }})</h4>
        <div v-for="p in selectedObject.properties" :key="p.apiName" class="studio__prop-row">
          <span class="studio__prop-name">{{ p.displayName }}</span>
          <span class="studio__prop-type">{{ p.dataType }}</span>
          <span v-if="p.required" class="studio__prop-required">必填</span>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { studioApi, type StudioTBox, type StudioABox, type StudioRBox, type StudioStats, type StudioObjectType, type StudioHydration } from '../../api/studio'
import StudioCardView from './StudioCardView.vue'
import StudioThreeBox from './StudioThreeBox.vue'

const tbox = ref<StudioTBox | null>(null)
const abox = ref<StudioABox | null>(null)
const rbox = ref<StudioRBox | null>(null)
const stats = ref<StudioStats | null>(null)
const loading = ref(true)

const activeView = ref<'card' | 'threebox' | 'business' | 'twin' | 'flow'>('card')
const selectedObject = ref<StudioObjectType | null>(null)
const searchText = ref('')

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

function selectObject(o: StudioObjectType) {
  selectedObject.value = o
}

function formatNumber(n: number) {
  return n.toLocaleString('en-US')
}

onMounted(async () => {
  try {
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
  overflow: auto;
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

.studio__detail-section { padding: 14px 20px; border-bottom: 1px solid #f1f5f9; }
.studio__detail-section h4 { font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 10px; }
.studio__detail-desc { font-size: 12px; color: #64748b; line-height: 1.6; margin-bottom: 10px; }
.studio__detail-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.studio__tag {
  font-size: 10px;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 4px;
}
.studio__prop-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin-bottom: 4px;
  background: #f8fafc;
  border-radius: 4px;
  font-size: 12px;
}
.studio__prop-name { flex: 1; color: #1e293b; }
.studio__prop-type {
  font-size: 10px;
  background: #e2e8f0;
  color: #475569;
  padding: 1px 6px;
  border-radius: 3px;
}
.studio__prop-required {
  font-size: 10px;
  background: #fef3c7;
  color: #92400e;
  padding: 1px 6px;
  border-radius: 3px;
}
</style>
