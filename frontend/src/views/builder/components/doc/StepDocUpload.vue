<template>
  <div class="step-upload">
    <h2 class="step-upload__title">描述业务需求并上传文档</h2>
    <p class="step-upload__sub">上传业务相关文档（Excel/PDF/Word/PPT），AI 将从中提取本体实体、属性和关系</p>

    <div class="step-upload__tip">
      <span class="step-upload__tip-icon">💡</span>
      <span>首次使用？建议先 <a class="step-upload__tip-link" @click="handleDownloadTemplate">下载文档模板</a>，按模板结构整理业务资料后上传，抽取效果更佳</span>
    </div>

    <div class="step-upload__field">
      <label class="step-upload__label">业务需求描述</label>
      <textarea class="step-upload__textarea" v-model="desc" placeholder="例如：我需要构建宽带退单稽核的本体，包含客户、工单、退单原因等实体..." rows="4"></textarea>
    </div>

    <div class="step-upload__field">
      <label class="step-upload__label">上传文档</label>
      <div class="step-upload__dropzone"
           :class="{ 'step-upload__dropzone--active': dragging }"
           @dragover.prevent="dragging = true"
           @dragleave="dragging = false"
           @drop.prevent="onDrop">
        <div class="step-upload__dropzone-inner">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none"><path d="M12 16V4M12 4l-4 4M12 4l4 4" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 16v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2" stroke="#94a3b8" stroke-width="2" stroke-linecap="round"/></svg>
          <p>拖拽文件到此处，或 <span class="step-upload__link" @click="fileInput?.click()">点击选择</span></p>
          <p class="step-upload__hint">支持 .xlsx .xls .pdf .docx .doc .pptx .ppt .csv .txt</p>
        </div>
        <input ref="fileInput" type="file" multiple accept=".xlsx,.xls,.pdf,.docx,.doc,.pptx,.ppt,.csv,.txt,.md" style="display:none" @change="onFiles" />
      </div>
    </div>

    <div class="step-upload__file-list" v-if="files.length">
      <div v-for="(f, i) in files" :key="i" class="step-upload__file-item">
        <span class="step-upload__file-icon">{{ getFileIcon(f.name) }}</span>
        <span class="step-upload__file-name">{{ f.name }}</span>
        <span class="step-upload__file-size">{{ formatSize(f.size) }}</span>
        <button class="step-upload__file-del" @click="files.splice(i, 1)">×</button>
      </div>
    </div>

    <button class="step-upload__btn" :disabled="!canProceed || uploading" @click="handleStart">
      {{ uploading ? '上传解析中...' : '开始 AI 解析' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { uploadDocuments, downloadTemplate } from '../../../../api/docBuilder'

const emit = defineEmits<{ (e: 'next', payload: { sessionId: string; businessDesc: string }): void }>()

const desc = ref('')
const files = ref<File[]>([])
const uploading = ref(false)
const dragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const canProceed = computed(() => desc.value.trim() && files.value.length > 0)

function onFiles(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    files.value.push(...Array.from(input.files))
    input.value = ''
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false
  if (e.dataTransfer?.files) {
    files.value.push(...Array.from(e.dataTransfer.files))
  }
}

function getFileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  if (['xlsx', 'xls', 'csv'].includes(ext)) return '📊'
  if (['pdf'].includes(ext)) return '📄'
  if (['docx', 'doc'].includes(ext)) return '📝'
  if (['pptx', 'ppt'].includes(ext)) return '📑'
  return '📃'
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function handleDownloadTemplate() {
  downloadTemplate()
}

async function handleStart() {
  if (!canProceed.value) return
  uploading.value = true
  try {
    const resp = await uploadDocuments(files.value)
    emit('next', { sessionId: resp.data.session_id, businessDesc: desc.value })
  } catch {
    alert('上传失败，请重试')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.step-upload { max-width: 720px; margin: 0 auto; padding: 32px 24px; }
.step-upload__title { font-size: 20px; font-weight: 600; margin-bottom: 8px; color: #1a1a2e; }
.step-upload__sub { font-size: 13px; color: #666; margin-bottom: 16px; }
.step-upload__tip { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: #f0f6ff; border: 1px solid #d0e2ff; border-radius: 8px; margin-bottom: 20px; font-size: 13px; color: #333; }
.step-upload__tip-icon { font-size: 16px; }
.step-upload__tip-link { color: #4a6fa5; cursor: pointer; text-decoration: underline; font-weight: 500; }
.step-upload__tip-link:hover { color: #3d5f8c; }
.step-upload__field { margin-bottom: 20px; }
.step-upload__label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: #333; }
.step-upload__textarea { width: 100%; padding: 12px; border: 1px solid #d0d0d0; border-radius: 8px; font-size: 14px; resize: vertical; font-family: inherit; }
.step-upload__textarea:focus { outline: none; border-color: #4a6fa5; }
.step-upload__dropzone { border: 2px dashed #d0d0d0; border-radius: 12px; padding: 32px; text-align: center; transition: border-color 0.2s, background 0.2s; cursor: pointer; }
.step-upload__dropzone:hover, .step-upload__dropzone--active { border-color: #4a6fa5; background: #f0f6ff; }
.step-upload__dropzone-inner p { margin: 8px 0 0; font-size: 13px; color: #666; }
.step-upload__hint { font-size: 11px !important; color: #999 !important; }
.step-upload__link { color: #4a6fa5; cursor: pointer; text-decoration: underline; }
.step-upload__file-list { margin-bottom: 20px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.step-upload__file-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.step-upload__file-item:last-child { border-bottom: none; }
.step-upload__file-icon { font-size: 18px; }
.step-upload__file-name { flex: 1; font-size: 13px; font-weight: 500; word-break: break-all; }
.step-upload__file-size { font-size: 11px; color: #999; }
.step-upload__file-del { width: 22px; height: 22px; border: none; background: #fee; color: #d00; border-radius: 4px; cursor: pointer; font-size: 14px; line-height: 1; }
.step-upload__btn { margin-top: 12px; padding: 10px 24px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-upload__btn:disabled { opacity: 0.5; cursor: default; }
.step-upload__btn:hover:not(:disabled) { background: #3d5f8c; }
</style>
