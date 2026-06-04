<template>
  <div class="step-assets">
    <h2 class="step-assets__title">选择本体资产</h2>
    <p class="step-assets__sub">选择用于生成技能的实体、规则、函数和动作</p>

    <div class="step-assets__layout">
      <div class="step-assets__left">
        <div class="step-assets__tabs">
          <button v-for="tab in tabs" :key="tab.key" class="step-assets__tab" :class="{ 'step-assets__tab--active': activeTab === tab.key }" @click="activeTab = tab.key">
            {{ tab.label }} ({{ items[tab.key]?.length || 0 }})
          </button>
        </div>
        <input class="step-assets__search" v-model="search" placeholder="搜索..." />
        <div class="step-assets__items">
          <label v-for="item in filteredItems" :key="item.id" class="step-assets__item">
            <input type="checkbox" :checked="isSelected(activeTab, item.id)" @change="toggle(activeTab, item.id)" />
            <span class="step-assets__item-name">{{ item.name_zh || item.name }}</span>
            <span class="step-assets__item-sub">{{ item.name }}</span>
          </label>
          <p v-if="!filteredItems.length" class="step-assets__empty">暂无数据</p>
        </div>
      </div>

      <div class="step-assets__right">
        <h3 class="step-assets__right-title">已选资产 ({{ totalSelected }})</h3>
        <div v-for="tab in tabs" :key="tab.key">
          <div v-if="selected[tab.key]?.length" class="step-assets__selected-group">
            <span class="step-assets__selected-label">{{ tab.label }}</span>
            <div v-for="id in selected[tab.key]" :key="id" class="step-assets__selected-item">
              <span>{{ getItemName(tab.key, id) }}</span>
              <button class="step-assets__remove" @click="toggle(tab.key, id)">×</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <button class="step-assets__btn" :disabled="totalSelected === 0 || loading" @click="handleNext">
      {{ loading ? '创建会话...' : '下一步' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import client from '../../../api/client'
import { createGenSession } from '../../../api/skillGen'

const emit = defineEmits<{ (e: 'next', payload: { sessionId: string; assetsContext: string }): void }>()

const tabs = [
  { key: 'entities', label: '实体' },
  { key: 'rules', label: '规则' },
  { key: 'functions', label: '函数' },
  { key: 'actions', label: '动作' },
]

const activeTab = ref('entities')
const search = ref('')
const loading = ref(false)
const items = ref<Record<string, any[]>>({ entities: [], rules: [], functions: [], actions: [] })
const selected = ref<Record<string, string[]>>({ entities: [], rules: [], functions: [], actions: [] })

const filteredItems = computed(() => {
  const list = items.value[activeTab.value] || []
  if (!search.value) return list
  const q = search.value.toLowerCase()
  return list.filter((i: any) => (i.name || '').toLowerCase().includes(q) || (i.name_zh || '').toLowerCase().includes(q))
})

const totalSelected = computed(() => Object.values(selected.value).reduce((sum, arr) => sum + arr.length, 0))

function isSelected(tab: string, id: string) {
  return selected.value[tab]?.includes(id)
}

function toggle(tab: string, id: string) {
  const arr = selected.value[tab]
  const idx = arr.indexOf(id)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(id)
}

function getItemName(tab: string, id: string) {
  const item = items.value[tab]?.find((i: any) => i.id === id)
  return item ? (item.name_zh || item.name) : id
}

async function handleNext() {
  loading.value = true
  try {
    const resp = await createGenSession(selected.value)
    emit('next', { sessionId: resp.data.session_id, assetsContext: resp.data.assets_context })
  } catch { alert('创建会话失败') }
  finally { loading.value = false }
}

onMounted(async () => {
  const [entities, rules, functions, actions] = await Promise.all([
    client.get('/entities').then(r => r.data),
    client.get('/rules').then(r => r.data),
    client.get('/functions').then(r => r.data),
    client.get('/actions').then(r => r.data),
  ])
  items.value = { entities, rules, functions, actions }
})
</script>

<style scoped>
.step-assets__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.step-assets__sub { font-size: 13px; color: #666; margin-bottom: 20px; }
.step-assets__layout { display: flex; gap: 20px; margin-bottom: 20px; }
.step-assets__left { flex: 1; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
.step-assets__tabs { display: flex; gap: 4px; margin-bottom: 12px; }
.step-assets__tab { padding: 6px 12px; border: 1px solid #e0e0e0; border-radius: 4px; background: #fff; font-size: 12px; cursor: pointer; }
.step-assets__tab--active { background: #4a6fa5; color: #fff; border-color: #4a6fa5; }
.step-assets__search { width: 100%; padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 6px; font-size: 13px; margin-bottom: 12px; }
.step-assets__items { max-height: 300px; overflow-y: auto; }
.step-assets__item { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 4px; cursor: pointer; }
.step-assets__item:hover { background: #f5f5f5; }
.step-assets__item-name { font-size: 13px; font-weight: 500; }
.step-assets__item-sub { font-size: 11px; color: #999; }
.step-assets__empty { text-align: center; color: #999; font-size: 13px; padding: 20px; }
.step-assets__right { width: 280px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
.step-assets__right-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.step-assets__selected-group { margin-bottom: 12px; }
.step-assets__selected-label { font-size: 11px; color: #999; display: block; margin-bottom: 4px; }
.step-assets__selected-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: #f0f6ff; border-radius: 4px; margin-bottom: 4px; font-size: 12px; }
.step-assets__remove { border: none; background: none; color: #d00; cursor: pointer; font-size: 16px; }
.step-assets__btn { margin-top: 12px; padding: 10px 24px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-assets__btn:disabled { opacity: 0.5; cursor: default; }
</style>
