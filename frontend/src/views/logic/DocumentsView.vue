<template>
  <div class="logic-page">
    <BuilderReturnBanner kind-label="业务文档" />
    <div class="logic-page__header">
      <div>
        <h1 class="text-display">业务文档库</h1>
        <p class="text-caption" style="margin-top:4px;">Word / Excel / PDF · 对话生成模式可勾选</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="fileInput?.click()">
          ＋ 上传文档
        </button>
        <input ref="fileInput" type="file" multiple accept=".docx,.pdf,.xlsx,.xls,.csv,.md,.txt" style="display:none" @change="onFiles" />
      </div>
    </div>

    <div class="logic-page__filter">
      <input v-model="search" class="logic-search" placeholder="搜索文档名…" />
    </div>

    <div class="logic-page__list">
      <div v-for="d in filtered" :key="d.id" class="rule-card">
        <div class="rule-card__header">
          <span class="rule-card__name text-body-medium">{{ d.name }}</span>
          <span class="rule-card__entity text-caption">{{ d.file_type.toUpperCase() }} · {{ Math.round(d.size_bytes / 1024) }} KB</span>
          <button class="btn-sm-del" @click="onDelete(d)">删除</button>
        </div>
        <div v-if="d.summary" class="rule-card__detail">
          <div class="rule-detail-row">
            <span class="rule-detail-label">摘要</span>
            <span>{{ d.summary }}</span>
          </div>
        </div>
      </div>
      <div v-if="!filtered.length" class="logic-empty">
        <p class="text-caption">还没有文档 — 点右上角上传</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { get, del } from '../../api/client'
import BuilderReturnBanner from '../../components/common/BuilderReturnBanner.vue'

interface Doc { id: string; name: string; file_type: string; size_bytes: number; summary: string; domain_tags: string[]; uploaded_at: string }

const docs = ref<Doc[]>([])
const search = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const filtered = computed(() => {
  if (!search.value.trim()) return docs.value
  const s = search.value.toLowerCase()
  return docs.value.filter(d => d.name.toLowerCase().includes(s) || (d.summary || '').toLowerCase().includes(s))
})

async function fetchDocs() {
  docs.value = await get<Doc[]>('/business-documents')
}

async function onFiles(e: Event) {
  const list = (e.target as HTMLInputElement).files
  if (!list) return
  for (const f of Array.from(list)) {
    const fd = new FormData()
    fd.append('file', f, f.name)
    const resp = await fetch('/api/v1/business-documents/upload', { method: 'POST', body: fd })
    if (!resp.ok) {
      alert(`上传失败：${f.name}`)
      continue
    }
  }
  ;(e.target as HTMLInputElement).value = ''
  await fetchDocs()
}

async function onDelete(d: Doc) {
  if (!confirm(`确定删除文档「${d.name}」？`)) return
  await del<void>(`/business-documents/${d.id}`)
  await fetchDocs()
}

onMounted(fetchDocs)
</script>

<style scoped>
@import './logic-shared.css';
</style>
