<template>
  <div class="step-doc">
    <h2 class="step-doc__title">选择补充文档</h2>
    <p class="step-doc__sub">从文档库中选择与业务相关的非结构化文档，用于补充实体和关系的中文名称及业务含义</p>

    <div class="step-doc__filter">
      <input class="step-doc__input" v-model="filter" placeholder="按文件名过滤..." />
    </div>

    <div class="step-doc__list" v-if="!loading">
      <label v-for="doc in filteredDocs" :key="doc.key" class="step-doc__item">
        <input type="checkbox" :value="doc.key" v-model="selectedKeys" />
        <div class="step-doc__item-info">
          <div class="step-doc__item-title">{{ doc.title }}</div>
          <div class="step-doc__item-meta">{{ formatSize(doc.size) }} · {{ doc.last_modified?.slice(0, 10) || '' }}</div>
        </div>
      </label>
      <div v-if="!filteredDocs.length" class="step-doc__empty">无匹配文档</div>
    </div>
    <div v-else class="step-doc__loading">加载文档列表中...</div>

    <div class="step-doc__actions">
      <button class="step-doc__btn step-doc__btn--skip" @click="emit('next', [])">跳过，不使用文档</button>
      <button class="step-doc__btn" :disabled="!selectedKeys.length" @click="emit('next', selectedKeys)">
        已选 {{ selectedKeys.length }} 篇文档 → 开始提取
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDocuments } from '../../../../api/aiBuilderV2'
import type { DocInfo } from '../../../../api/aiBuilderV2'

const props = defineProps<{ businessDesc: string }>()
const emit = defineEmits<{ (e: 'next', keys: string[]): void }>()

const docs = ref<DocInfo[]>([])
const loading = ref(true)
const filter = ref('')
const selectedKeys = ref<string[]>([])

const filteredDocs = computed(() => {
  if (!filter.value) return docs.value
  const q = filter.value.toLowerCase()
  return docs.value.filter(d => d.title.toLowerCase().includes(q))
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

onMounted(async () => {
  try {
    const resp = await getDocuments()
    docs.value = resp.data.documents
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.step-doc { max-width: 800px; margin: 0 auto; padding: 24px; }
.step-doc__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.step-doc__sub { font-size: 13px; color: #666; margin-bottom: 16px; }
.step-doc__filter { margin-bottom: 12px; }
.step-doc__input { width: 100%; padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 13px; }
.step-doc__list { max-height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; }
.step-doc__item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; }
.step-doc__item:hover { background: #f8f9fa; }
.step-doc__item:last-child { border-bottom: none; }
.step-doc__item-info { flex: 1; }
.step-doc__item-title { font-size: 13px; font-weight: 500; word-break: break-all; }
.step-doc__item-meta { font-size: 11px; color: #999; margin-top: 2px; }
.step-doc__empty { padding: 24px; text-align: center; color: #999; }
.step-doc__loading { padding: 24px; text-align: center; color: #666; }
.step-doc__actions { margin-top: 16px; display: flex; gap: 12px; justify-content: flex-end; }
.step-doc__btn { padding: 10px 24px; background: #2e7d32; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-doc__btn:disabled { opacity: 0.5; cursor: default; }
.step-doc__btn--skip { background: transparent; color: #666; border: 1px solid #d0d0d0; }
</style>
