<template>
  <div class="asset-picker">
    <h2 class="asset-picker__title">选择数据表</h2>
    <p class="asset-picker__sub">从已注册且包含结构信息的数据资产中选择本体的数据来源</p>

    <div class="asset-picker__toolbar">
      <input v-model="filter" class="asset-picker__search" placeholder="搜索表名或描述..." />
      <button class="asset-picker__recommend" :disabled="recommending || !tables.length" @click="loadRecommendations">
        {{ recommending ? '推荐中...' : 'AI 推荐' }}
      </button>
    </div>

    <p v-if="notice" class="asset-picker__notice">{{ notice }}</p>
    <div v-if="loading" class="asset-picker__empty">正在加载数据资产...</div>
    <div v-else-if="errorMessage" class="asset-picker__error">{{ errorMessage }}</div>
    <div v-else-if="tables.length" class="asset-picker__table-list">
      <label
        v-for="table in filteredTables"
        :key="table.asset_id"
        class="asset-picker__table-item"
        :class="{ 'asset-picker__table-item--recommended': recommendedSet.has(table.table_name) }"
      >
        <input v-model="selectedTables" type="checkbox" :value="table.table_name" />
        <span class="asset-picker__table-name">{{ table.table_name }}</span>
        <span class="asset-picker__table-desc">{{ table.table_desc }}</span>
        <span v-if="table.domain" class="asset-picker__table-tag">{{ table.domain }}</span>
        <span v-if="recommendedSet.has(table.table_name)" class="asset-picker__badge">AI推荐</span>
      </label>
      <div v-if="!filteredTables.length" class="asset-picker__empty">没有匹配的数据表</div>
    </div>
    <div v-else class="asset-picker__empty">暂无可用数据表，请先在数据接入页面注册并同步结构</div>

    <button class="asset-picker__next" :disabled="!selectedTables.length" @click="emit('next', selectedTables)">
      已选 {{ selectedTables.length }} 张表 → 下一步：选择文档
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listTables, recommendTables } from '../../../../api/aiBuilderV2'
import type { TableInfo } from '../../../../api/aiBuilderV2'

const props = defineProps<{ businessDesc: string }>()
const emit = defineEmits<{ (e: 'next', tables: string[]): void }>()

const tables = ref<TableInfo[]>([])
const selectedTables = ref<string[]>([])
const recommendedTables = ref<string[]>([])
const loading = ref(true)
const recommending = ref(false)
const errorMessage = ref('')
const notice = ref('')
const filter = ref('')

const recommendedSet = computed(() => new Set(recommendedTables.value))
const filteredTables = computed(() => {
  const query = filter.value.trim().toLowerCase()
  if (!query) return tables.value
  return tables.value.filter(table =>
    table.table_name.toLowerCase().includes(query) || table.table_desc.toLowerCase().includes(query),
  )
})

async function loadRecommendations() {
  recommending.value = true
  notice.value = ''
  try {
    const response = await recommendTables(props.businessDesc)
    recommendedTables.value = response.data.recommended
    selectedTables.value = [...response.data.recommended]
  } catch (error: any) {
    notice.value = error?.response?.data?.detail || error?.message || 'AI 推荐暂不可用，可手动选择数据表'
  } finally {
    recommending.value = false
  }
}

onMounted(async () => {
  try {
    const response = await listTables()
    tables.value = response.data.tables
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.detail || error?.message || '数据资产加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.asset-picker { max-width: 900px; margin: 0 auto; padding: 24px; }
.asset-picker__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.asset-picker__sub { font-size: 13px; color: #666; margin-bottom: 20px; }
.asset-picker__toolbar { display: flex; gap: 10px; margin-bottom: 10px; }
.asset-picker__search { flex: 1; padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 13px; }
.asset-picker__search:focus { outline: none; border-color: #4a6fa5; }
.asset-picker__recommend, .asset-picker__next { padding: 9px 18px; border: none; border-radius: 6px; background: #4a6fa5; color: #fff; cursor: pointer; }
.asset-picker__recommend:disabled, .asset-picker__next:disabled { opacity: 0.5; cursor: default; }
.asset-picker__notice { margin: 8px 0; color: #8a6100; font-size: 12px; }
.asset-picker__error { padding: 20px; color: #d32f2f; text-align: center; }
.asset-picker__table-list { max-height: 420px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; }
.asset-picker__table-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; font-size: 13px; }
.asset-picker__table-item:last-child { border-bottom: none; }
.asset-picker__table-item:hover { background: #f8f9fa; }
.asset-picker__table-item--recommended { background: #f0fff0; }
.asset-picker__table-name { min-width: 220px; font-family: monospace; font-size: 12px; font-weight: 500; }
.asset-picker__table-desc { flex: 1; color: #555; }
.asset-picker__table-tag { padding: 2px 6px; border-radius: 4px; background: #e8e8e8; color: #666; font-size: 10px; }
.asset-picker__badge { padding: 2px 6px; border-radius: 8px; background: #2e7d32; color: #fff; font-size: 9px; }
.asset-picker__empty { padding: 24px; text-align: center; color: #888; font-size: 13px; }
.asset-picker__next { margin-top: 16px; background: #2e7d32; }
</style>
