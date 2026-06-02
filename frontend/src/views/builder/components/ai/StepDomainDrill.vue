<template>
  <div class="step-drill">
    <h2 class="step-drill__title">选择数据表</h2>
    <p class="step-drill__sub">当前主题域：<strong>{{ domain }}</strong>，请逐级下钻选择相关数据表</p>

    <!-- 二级主题域 -->
    <div class="step-drill__section">
      <div class="step-drill__label">二级主题域</div>
      <div class="step-drill__cards">
        <div v-for="d in subDomains" :key="d" class="step-drill__card" :class="{ 'step-drill__card--active': selectedSub === d }" @click="selectSub(d)">{{ d }}</div>
      </div>
    </div>

    <!-- 三级主题域 -->
    <div class="step-drill__section" v-if="selectedSub">
      <div class="step-drill__label">三级主题域</div>
      <div class="step-drill__cards">
        <div v-for="t in themes" :key="t" class="step-drill__card" :class="{ 'step-drill__card--active': selectedTheme === t }" @click="selectTheme(t)">{{ t }}</div>
      </div>
    </div>

    <!-- 表列表 -->
    <div class="step-drill__section" v-if="tables.length">
      <div class="step-drill__label">可用数据表（勾选需要的表）</div>
      <div class="step-drill__table-list">
        <label v-for="t in tables" :key="t.table_name" class="step-drill__table-item">
          <input type="checkbox" :value="t.table_name" v-model="selectedTables" />
          <span class="step-drill__table-name">{{ t.table_name }}</span>
          <span class="step-drill__table-desc">{{ t.table_desc }}</span>
          <span class="step-drill__table-tag">{{ t.layering }}</span>
        </label>
      </div>
    </div>

    <button class="step-drill__btn" :disabled="!selectedTables.length" @click="emit('next', selectedTables)">
      已选 {{ selectedTables.length }} 张表 → 下一步：选择文档
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getSubDomains, getThemes, getTables } from '../../../../api/aiBuilderV2'
import type { TableInfo } from '../../../../api/aiBuilderV2'

const props = defineProps<{ domain: string }>()
const emit = defineEmits<{ (e: 'next', tables: string[]): void }>()

const subDomains = ref<string[]>([])
const themes = ref<string[]>([])
const tables = ref<TableInfo[]>([])
const selectedSub = ref('')
const selectedTheme = ref('')
const selectedTables = ref<string[]>([])

onMounted(async () => {
  const resp = await getSubDomains(props.domain)
  subDomains.value = resp.data.sub_domains
})

async function selectSub(d: string) {
  selectedSub.value = d
  selectedTheme.value = ''
  tables.value = []
  const resp = await getThemes(props.domain, d)
  themes.value = resp.data.themes
  if (!themes.value.length) {
    const tResp = await getTables(props.domain, d)
    tables.value = tResp.data.tables
  }
}

async function selectTheme(t: string) {
  selectedTheme.value = t
  const resp = await getTables(props.domain, selectedSub.value, t)
  tables.value = resp.data.tables
}
</script>

<style scoped>
.step-drill { max-width: 900px; margin: 0 auto; padding: 24px; }
.step-drill__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.step-drill__sub { font-size: 13px; color: #666; margin-bottom: 20px; }
.step-drill__section { margin-bottom: 20px; }
.step-drill__label { font-size: 12px; font-weight: 600; color: #444; margin-bottom: 8px; }
.step-drill__cards { display: flex; flex-wrap: wrap; gap: 8px; }
.step-drill__card { padding: 8px 16px; border: 1px solid #d0d0d0; border-radius: 6px; cursor: pointer; font-size: 13px; }
.step-drill__card:hover { border-color: #4a6fa5; background: #f0f6ff; }
.step-drill__card--active { border-color: #4a6fa5; background: #e8f0fc; color: #4a6fa5; font-weight: 500; }
.step-drill__table-list { max-height: 320px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; }
.step-drill__table-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; font-size: 13px; }
.step-drill__table-item:hover { background: #f8f9fa; }
.step-drill__table-item:last-child { border-bottom: none; }
.step-drill__table-name { font-weight: 500; font-family: monospace; font-size: 12px; min-width: 240px; }
.step-drill__table-desc { color: #555; flex: 1; }
.step-drill__table-tag { font-size: 10px; background: #e8e8e8; padding: 2px 6px; border-radius: 4px; color: #666; }
.step-drill__btn { margin-top: 16px; padding: 10px 24px; background: #2e7d32; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-drill__btn:disabled { opacity: 0.5; cursor: default; }
</style>
