<template>
  <div class="step-drill">
    <h2 class="step-drill__title">选择数据表</h2>
    <p class="step-drill__sub">已选一级主题域：<strong>{{ domains.join('、') }}</strong>，请逐级下钻选择相关数据表</p>

    <!-- 二级主题域 -->
    <div class="step-drill__section">
      <div class="step-drill__label">二级主题域（可多选）</div>
      <div class="step-drill__cards">
        <div v-for="d in subDomains" :key="d" class="step-drill__card" :class="{ 'step-drill__card--active': selectedSubs.includes(d) }" @click="toggleSub(d)">{{ d }}</div>
      </div>
    </div>

    <!-- 三级主题域 -->
    <div class="step-drill__section" v-if="themes.length">
      <div class="step-drill__label">三级主题域（可多选）</div>
      <div class="step-drill__cards">
        <div v-for="t in themes" :key="t" class="step-drill__card" :class="{ 'step-drill__card--active': selectedThemes.includes(t) }" @click="toggleTheme(t)">{{ t }}</div>
      </div>
    </div>

    <!-- 加载表 -->
    <div class="step-drill__section" v-if="selectedSubs.length">
      <button class="step-drill__btn step-drill__btn--load" :disabled="loadingTables" @click="loadAndRecommend">
        {{ loadingTables ? '加载推荐中...' : '加载并智能推荐数据表' }}
      </button>
      <p v-if="errorMsg" class="step-drill__error">{{ errorMsg }}</p>
    </div>

    <!-- 表列表 -->
    <div class="step-drill__section" v-if="tables.length">
      <div class="step-drill__label">
        可用数据表（AI已自动推荐，可调整勾选）
        <span class="step-drill__hint">共 {{ tables.length }} 张，已选 {{ selectedTables.length }} 张</span>
      </div>
      <div class="step-drill__table-list">
        <label v-for="t in tables" :key="t.table_name" class="step-drill__table-item" :class="{ 'step-drill__table-item--recommended': recommendedSet.has(t.table_name) }">
          <input type="checkbox" :value="t.table_name" v-model="selectedTables" />
          <span class="step-drill__table-name">{{ t.table_name }}</span>
          <span class="step-drill__table-desc">{{ t.table_desc }}</span>
          <span class="step-drill__table-tag">{{ t.layering }}</span>
          <span v-if="recommendedSet.has(t.table_name)" class="step-drill__rec-badge">AI推荐</span>
        </label>
      </div>
    </div>

    <button class="step-drill__btn" :disabled="!selectedTables.length" @click="emit('next', selectedTables)">
      已选 {{ selectedTables.length }} 张表 → 下一步：选择文档
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getSubDomains, getThemes, recommendTables } from '../../../../api/aiBuilderV2'
import type { TableInfo } from '../../../../api/aiBuilderV2'

const props = defineProps<{ domains: string[]; businessDesc: string }>()
const emit = defineEmits<{ (e: 'next', tables: string[]): void }>()

const subDomains = ref<string[]>([])
const themes = ref<string[]>([])
const tables = ref<TableInfo[]>([])
const selectedSubs = ref<string[]>([])
const selectedThemes = ref<string[]>([])
const selectedTables = ref<string[]>([])
const recommendedTables = ref<string[]>([])
const loadingTables = ref(false)
const errorMsg = ref('')

const recommendedSet = computed(() => new Set(recommendedTables.value))

onMounted(async () => {
  const allSubs: string[] = []
  for (const domain of props.domains) {
    const resp = await getSubDomains(domain)
    allSubs.push(...resp.data.sub_domains)
  }
  subDomains.value = [...new Set(allSubs)]
})

function toggleSub(d: string) {
  const idx = selectedSubs.value.indexOf(d)
  if (idx >= 0) {
    selectedSubs.value.splice(idx, 1)
  } else {
    selectedSubs.value.push(d)
  }
  loadThemes()
}

function toggleTheme(t: string) {
  const idx = selectedThemes.value.indexOf(t)
  if (idx >= 0) {
    selectedThemes.value.splice(idx, 1)
  } else {
    selectedThemes.value.push(t)
  }
}

async function loadThemes() {
  const allThemes: string[] = []
  for (const domain of props.domains) {
    for (const sub of selectedSubs.value) {
      const resp = await getThemes(domain, sub)
      allThemes.push(...resp.data.themes)
    }
  }
  themes.value = [...new Set(allThemes)]
  selectedThemes.value = selectedThemes.value.filter(t => themes.value.includes(t))
}

async function loadAndRecommend() {
  loadingTables.value = true
  errorMsg.value = ''
  try {
    const resp = await recommendTables(
      props.businessDesc,
      props.domains,
      selectedSubs.value,
      selectedThemes.value.length ? selectedThemes.value : undefined,
    )
    tables.value = resp.data.tables
    recommendedTables.value = resp.data.recommended
    selectedTables.value = [...resp.data.recommended]
  } catch (e: any) {
    console.error(e)
    errorMsg.value = e?.response?.data?.detail || e?.message || '加载推荐数据表失败，请稍后重试'
  } finally {
    loadingTables.value = false
  }
}
</script>

<style scoped>
.step-drill { max-width: 900px; margin: 0 auto; padding: 24px; }
.step-drill__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.step-drill__sub { font-size: 13px; color: #666; margin-bottom: 20px; }
.step-drill__section { margin-bottom: 20px; }
.step-drill__label { font-size: 12px; font-weight: 600; color: #444; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.step-drill__hint { font-weight: 400; color: #888; font-size: 11px; }
.step-drill__cards { display: flex; flex-wrap: wrap; gap: 8px; }
.step-drill__card { padding: 8px 16px; border: 1px solid #d0d0d0; border-radius: 6px; cursor: pointer; font-size: 13px; }
.step-drill__card:hover { border-color: #4a6fa5; background: #f0f6ff; }
.step-drill__card--active { border-color: #4a6fa5; background: #e8f0fc; color: #4a6fa5; font-weight: 500; }
.step-drill__table-list { max-height: 360px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; }
.step-drill__table-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; font-size: 13px; }
.step-drill__table-item:hover { background: #f8f9fa; }
.step-drill__table-item:last-child { border-bottom: none; }
.step-drill__table-item--recommended { background: #f0fff0; }
.step-drill__table-name { font-weight: 500; font-family: monospace; font-size: 12px; min-width: 240px; }
.step-drill__table-desc { color: #555; flex: 1; }
.step-drill__table-tag { font-size: 10px; background: #e8e8e8; padding: 2px 6px; border-radius: 4px; color: #666; }
.step-drill__rec-badge { font-size: 9px; background: #2e7d32; color: #fff; padding: 2px 6px; border-radius: 8px; }
.step-drill__btn { margin-top: 16px; padding: 10px 24px; background: #2e7d32; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-drill__btn:disabled { opacity: 0.5; cursor: default; }
.step-drill__btn--load { background: #4a6fa5; }
.step-drill__btn--load:hover:not(:disabled) { background: #3d5f8c; }
.step-drill__error { color: #d32f2f; font-size: 12px; margin-top: 8px; }
</style>