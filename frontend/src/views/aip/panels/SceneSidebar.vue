<template>
  <aside class="aip-sb">
    <!-- 头部 -->
    <div class="aip-sb__head">
      <span class="aip-sb__title">场景管理</span>
      <button class="aip-sb__add-btn" @click="$emit('open-import')" title="导入场景">+</button>
    </div>

    <!-- 搜索 -->
    <div class="aip-sb__search">
      <span class="aip-sb__search-icon">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
      </span>
      <input class="aip-sb__search-input" v-model="keyword" placeholder="搜索场景..." />
    </div>

    <!-- 分组列表 -->
    <div class="aip-sb__list">
      <div v-for="g in groups" :key="g.label" class="aip-sb__group">
        <div class="aip-sb__group-head" @click="toggle(g.label)">
          <svg class="aip-sb__chev" :class="{ open: expanded[g.label] !== false }" width="10" height="10" viewBox="0 0 12 12" fill="none">
            <path d="M4 3l4 3-4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="aip-sb__group-label">{{ g.label }}</span>
          <span class="aip-sb__group-count">{{ g.scenes.length }}</span>
        </div>
        <div v-if="expanded[g.label] !== false" class="aip-sb__group-body">
          <div v-if="!g.scenes.length" class="aip-sb__empty">暂无场景</div>
          <div v-for="s in g.scenes" :key="s.id"
            class="aip-sb__card" :class="{ active: s.id === store.currentSceneId }"
            @click="store.switchScene(s.id)">
            <div class="aip-sb__card-icon" :style="{ background: '#2E5BFF' }">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 1v6h6L8 15V9H2L8 1z" fill="#fff"/></svg>
            </div>
            <div class="aip-sb__card-info">
              <div class="aip-sb__card-name">{{ s.name }}</div>
              <div class="aip-sb__card-trigger">{{ triggerText(s) }}</div>
            </div>
            <span class="aip-sb__card-status" :class="`aip-sb__card-status--${s.status}`">{{ s.status === 'published' ? '已发布' : '草稿' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 当前场景信息（底部） -->
    <div v-if="store.currentScene" class="aip-sb__current">
      <div class="aip-sb__current-row">
        <span class="aip-sb__current-label">当前场景</span>
        <button class="aip-sb__danger-btn" @click="onDelete" title="删除场景">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V2h4v2M5 4v9h6V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div class="aip-sb__current-desc">{{ store.currentScene.description }}</div>
      <div class="aip-sb__trigger" :class="`aip-sb__trigger--${triggerLevel(store.currentScene)}`"
        @click="openTrigger">
        <span class="aip-sb__trigger-icon" v-html="triggerIcon(store.currentScene)"></span>
        <span class="aip-sb__trigger-text">{{ triggerText(store.currentScene) }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useAipStore } from '../../../store/aip'
import { SCENE_GROUPS, type SceneMeta } from '../aipData'

const store = useAipStore()
const emit = defineEmits<{ (e: 'open-import'): void }>()

const keyword = ref('')
const expanded = reactive<Record<string, boolean>>({})

function toggle(label: string) {
  expanded[label] = expanded[label] === false ? true : false
}

const groups = computed(() => SCENE_GROUPS.map(g => ({
  label: g.label,
  scenes: store.scenes
    .filter(s => s.group === g.label)
    .filter(s => !keyword.value || s.name.includes(keyword.value) || s.id.includes(keyword.value)),
})))

function triggerText(s: SceneMeta) {
  const t = s.triggerConfig
  if (!t.enabled) return '触发已暂停'
  if (t.type === 'schedule' && t.schedule) return `定时 · ${pad(t.schedule.hour)}:${pad(t.schedule.minute)}`
  if (t.type === 'event') return '事件触发'
  if (t.type === 'webhook') return 'Webhook'
  if (t.type === 'manual') return '手动触发'
  return '未配置触发'
}
function triggerLevel(s: SceneMeta) {
  if (!s.triggerConfig.enabled) return 'paused'
  return s.triggerConfig.type
}
function triggerIcon(s: SceneMeta) {
  const t = s.triggerConfig
  if (!t.enabled) return '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><rect x="4" y="3" width="3" height="10" fill="currentColor"/><rect x="9" y="3" width="3" height="10" fill="currentColor"/></svg>'
  if (t.type === 'schedule') return '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 4v4l3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
  if (t.type === 'event') return '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 1l2 5h5l-4 3 2 6-5-3.5-5 3.5 2-6L1 6h5l2-5z" stroke="currentColor" stroke-width="1.3"/></svg>'
  if (t.type === 'webhook') return '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="5" cy="8" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M11 8l-4 5M5 11l-3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
  return '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M5 3l9 5-9 5V3z" fill="currentColor"/></svg>'
}
function pad(n: number) { return String(n).padStart(2, '0') }

function openTrigger() {
  store.sceneDrawerOpen = true
  store.sceneDrawerTab = 'trigger'
}

function onDelete() {
  if (!store.currentScene) return
  if (!confirm(`确定删除场景「${store.currentScene.name}」？`)) return
  const id = store.currentSceneId
  const idx = store.scenes.findIndex(s => s.id === id)
  if (idx !== -1) store.scenes.splice(idx, 1)
  delete store.sceneData[id]
  if (store.scenes.length) store.switchScene(store.scenes[0].id)
}
</script>

<style scoped>
.aip-sb {
  width: 240px; min-width: 240px;
  background: #fff; border-right: 1px solid #f0f0f0;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.aip-sb__head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 14px 8px;
}
.aip-sb__title { font-weight: 700; font-size: 13px; color: #1e293b; }
.aip-sb__add-btn {
  width: 24px; height: 24px; border-radius: 50%;
  border: none; background: #2E5BFF; color: #fff;
  font-size: 16px; line-height: 1; cursor: pointer;
}
.aip-sb__add-btn:hover { background: #1d4ed8; }

.aip-sb__search {
  display: flex; align-items: center; gap: 6px;
  margin: 0 14px 10px;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;
  padding: 4px 8px;
}
.aip-sb__search-icon { color: #94a3b8; display: flex; }
.aip-sb__search-input { border: none; outline: none; background: transparent; width: 100%; font-size: 12px; }

.aip-sb__list { flex: 1; overflow-y: auto; padding: 0 8px 12px; }
.aip-sb__group { margin-bottom: 6px; }
.aip-sb__group-head {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px;
  cursor: pointer; user-select: none;
  font-size: 11px; color: #475569; font-weight: 600;
}
.aip-sb__group-head:hover { background: #f8fafc; border-radius: 4px; }
.aip-sb__chev { transition: transform .15s; flex-shrink: 0; color: #94a3b8; }
.aip-sb__chev.open { transform: rotate(90deg); }
.aip-sb__group-label { flex: 1; }
.aip-sb__group-count { font-size: 10px; color: #94a3b8; background: #f1f5f9; padding: 0 6px; border-radius: 8px; }
.aip-sb__group-body { display: flex; flex-direction: column; gap: 4px; padding: 4px 0 0; }

.aip-sb__empty { padding: 8px 12px; color: #cbd5e1; font-size: 11px; text-align: center; }

.aip-sb__card {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px;
  border: 1.5px solid transparent; border-radius: 6px;
  cursor: pointer;
  transition: border-color .15s, background .15s;
}
.aip-sb__card:hover { background: #f8f9fa; }
.aip-sb__card.active { border-color: #2E5BFF; background: rgba(46,91,255,.05); }

.aip-sb__card-icon {
  width: 28px; height: 28px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.aip-sb__card-info { flex: 1; min-width: 0; }
.aip-sb__card-name {
  font-size: 12px; font-weight: 600; color: #1e293b;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.aip-sb__card-trigger { font-size: 10px; color: #94a3b8; margin-top: 2px; }
.aip-sb__card-status {
  font-size: 9px; padding: 1px 6px; border-radius: 999px;
  white-space: nowrap; flex-shrink: 0;
}
.aip-sb__card-status--published { background: #ecfdf5; color: #10b981; }
.aip-sb__card-status--draft { background: #fffbeb; color: #f59e0b; }

.aip-sb__current {
  border-top: 1px solid #f0f0f0;
  padding: 10px 14px; flex-shrink: 0;
}
.aip-sb__current-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.aip-sb__current-label { font-size: 10px; color: #94a3b8; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase; }
.aip-sb__danger-btn {
  width: 22px; height: 22px; border-radius: 4px;
  border: none; background: transparent; color: #94a3b8; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.aip-sb__danger-btn:hover { background: #fef2f2; color: #ef4444; }
.aip-sb__current-desc {
  font-size: 11px; color: #64748b; line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}
.aip-sb__trigger {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 8px;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;
  font-size: 11px; cursor: pointer;
}
.aip-sb__trigger:hover { border-color: #2E5BFF; }
.aip-sb__trigger-icon { display: flex; }
.aip-sb__trigger--schedule { color: #2563eb; background: #eff6ff; border-color: #bfdbfe; }
.aip-sb__trigger--event { color: #7c3aed; background: #f5f3ff; border-color: #ddd6fe; }
.aip-sb__trigger--webhook { color: #0891b2; background: #ecfeff; border-color: #a5f3fc; }
.aip-sb__trigger--manual { color: #475569; }
.aip-sb__trigger--paused { color: #94a3b8; }
</style>
