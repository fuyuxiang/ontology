<template>
  <div class="step-doc">
    <h2 class="step-doc__title">选择补充文档</h2>
    <p class="step-doc__sub">从文档库中选择与业务相关的非结构化文档，或直接上传本地文件</p>

    <div class="step-doc__toolbar">
      <input class="step-doc__input" v-model="filter" placeholder="按文件名过滤..." />
      <button class="step-doc__upload-btn" @click="fileInput?.click()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 16V4M12 4l-4 4M12 4l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 16v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        上传文件
      </button>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".xlsx,.xls,.pdf,.docx,.doc,.pptx,.ppt,.csv,.txt,.md"
        style="display:none"
        @change="onFileSelect"
      />
    </div>

    <div v-if="uploadedFiles.length" class="step-doc__uploaded">
      <div class="step-doc__uploaded-head">本地上传（{{ uploadedFiles.length }}）</div>
      <div v-for="f in uploadedFiles" :key="f.key" class="step-doc__uploaded-item">
        <span class="step-doc__uploaded-icon">📄</span>
        <span class="step-doc__uploaded-name">{{ f.title }}</span>
        <span class="step-doc__uploaded-size">{{ formatSize(f.size) }}</span>
        <span v-if="f.uploading" class="step-doc__uploaded-status">上传中...</span>
        <span v-else-if="f.error" class="step-doc__uploaded-status step-doc__uploaded-status--err">失败</span>
        <span v-else class="step-doc__uploaded-status step-doc__uploaded-status--ok">已就绪</span>
        <button class="step-doc__uploaded-del" @click="removeUploaded(f.key)">×</button>
      </div>
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
      <button class="step-doc__btn" :disabled="!allSelectedKeys.length || hasUploading" @click="emit('next', allSelectedKeys)">
        已选 {{ allSelectedKeys.length }} 篇文档 → 开始提取
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDocuments } from '../../../../api/aiBuilderV2'
import { uploadDocuments } from '../../../../api/docBuilder'
import type { DocInfo } from '../../../../api/aiBuilderV2'

interface UploadedDoc {
  key: string
  title: string
  size: number
  uploading: boolean
  error: boolean
}

const props = defineProps<{ businessDesc: string }>()
const emit = defineEmits<{ (e: 'next', keys: string[]): void }>()

const docs = ref<DocInfo[]>([])
const loading = ref(true)
const filter = ref('')
const selectedKeys = ref<string[]>([])
const uploadedFiles = ref<UploadedDoc[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const filteredDocs = computed(() => {
  if (!filter.value) return docs.value
  const q = filter.value.toLowerCase()
  return docs.value.filter(d => d.title.toLowerCase().includes(q))
})

const hasUploading = computed(() => uploadedFiles.value.some(f => f.uploading))
const allSelectedKeys = computed(() => [
  ...selectedKeys.value,
  ...uploadedFiles.value.filter(f => !f.uploading && !f.error).map(f => f.key),
])

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function removeUploaded(key: string) {
  uploadedFiles.value = uploadedFiles.value.filter(f => f.key !== key)
}

async function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  const files = Array.from(input.files)
  input.value = ''

  const entries: UploadedDoc[] = files.map(f => ({
    key: `upload-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    title: f.name,
    size: f.size,
    uploading: true,
    error: false,
  }))
  uploadedFiles.value.push(...entries)

  try {
    const resp = await uploadDocuments(files)
    const returnedFiles = resp.data.files
    entries.forEach((entry, i) => {
      if (returnedFiles[i]) {
        entry.key = `doc-upload:${resp.data.session_id}:${returnedFiles[i].name}`
      }
      entry.uploading = false
    })
  } catch {
    entries.forEach(entry => {
      entry.uploading = false
      entry.error = true
    })
  }
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
.step-doc__toolbar { display: flex; gap: 10px; margin-bottom: 12px; align-items: center; }
.step-doc__input { flex: 1; padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 13px; }
.step-doc__upload-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 14px; border: 1px dashed #2e7d32; border-radius: 6px;
  background: #f0fdf4; color: #2e7d32; font-size: 13px; font-weight: 500;
  cursor: pointer; white-space: nowrap;
}
.step-doc__upload-btn:hover { background: #dcfce7; }
.step-doc__uploaded { margin-bottom: 12px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.step-doc__uploaded-head { padding: 8px 12px; font-size: 12px; font-weight: 600; background: #f8fafc; color: #475569; border-bottom: 1px solid #e0e0e0; }
.step-doc__uploaded-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.step-doc__uploaded-item:last-child { border-bottom: none; }
.step-doc__uploaded-icon { font-size: 14px; }
.step-doc__uploaded-name { flex: 1; word-break: break-all; }
.step-doc__uploaded-size { font-size: 11px; color: #999; }
.step-doc__uploaded-status { font-size: 11px; color: #2e7d32; }
.step-doc__uploaded-status--err { color: #d32f2f; }
.step-doc__uploaded-status--ok { color: #2e7d32; }
.step-doc__uploaded-del { border: none; background: none; color: #999; cursor: pointer; font-size: 16px; padding: 0 4px; }
.step-doc__uploaded-del:hover { color: #d32f2f; }
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
