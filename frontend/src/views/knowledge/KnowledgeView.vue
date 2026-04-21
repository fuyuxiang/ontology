<template>
  <div class="kb-page">
    <!-- 顶栏 -->
    <div class="kb-page__header">
      <div>
        <h1 class="text-display">多模态知识库</h1>
        <p class="text-caption" style="margin-top:4px">文档 · 图片 · 视频 · 多格式内容管理</p>
      </div>
      <div class="kb-header-right">
        <div class="kb-search-wrap">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" class="kb-search-icon"><circle cx="6.5" cy="6.5" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M10 10l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <input v-model="searchQ" class="kb-search" placeholder="搜索知识库内容..." @keyup.enter="doSearch" />
        </div>
        <button class="btn-primary" @click="openCreate">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          新建知识库
        </button>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div v-if="searchResults.length" class="kb-search-results">
      <div class="kb-search-results__header">
        <span>搜索「{{ lastSearchQ }}」共 {{ searchResults.length }} 条结果</span>
        <button class="kb-clear-search" @click="clearSearch">清除</button>
      </div>
      <div v-for="r in searchResults" :key="r.file_id" class="kb-search-item" @click="openKbById(r.kb_id)">
        <div class="kb-search-item__kb">{{ r.kb_name }}</div>
        <div class="kb-search-item__file">{{ r.file_name }}</div>
        <div class="kb-search-item__snippet">...{{ r.snippet }}...</div>
      </div>
    </div>

    <!-- 知识库卡片网格 -->
    <div v-if="!searchResults.length" class="kb-grid">
      <div v-if="loading" class="kb-empty">加载中...</div>
      <div v-else-if="!kbs.length" class="kb-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" style="color:#cbd5e1"><path d="M4 19.5A2.5 2.5 0 016.5 17H20" stroke="currentColor" stroke-width="1.5"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke="currentColor" stroke-width="1.5"/></svg>
        <p>暂无知识库，点击「新建知识库」开始</p>
      </div>
      <div v-for="kb in kbs" :key="kb.id" class="kb-card" @click="openKb(kb)">
        <div class="kb-card__header">
          <div class="kb-card__icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4 19.5A2.5 2.5 0 016.5 17H20" stroke="currentColor" stroke-width="1.5"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke="currentColor" stroke-width="1.5"/></svg>
          </div>
          <div class="kb-card__actions" @click.stop>
            <button class="kb-icon-btn" @click="openEdit(kb)" title="编辑">
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M11 2l3 3-9 9H2v-3l9-9z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
            </button>
            <button class="kb-icon-btn kb-icon-btn--danger" @click="handleDelete(kb)" title="删除">
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 10h8l1-10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
        </div>
        <div class="kb-card__name">{{ kb.name }}</div>
        <div class="kb-card__desc">{{ kb.description || '暂无描述' }}</div>
        <div class="kb-card__tags">
          <span v-for="tag in kb.tags.slice(0,3)" :key="tag" class="kb-tag">{{ tag }}</span>
        </div>
        <div class="kb-card__footer">
          <span class="kb-card__count">{{ kb.file_count }} 个文件</span>
          <span class="kb-card__time">{{ formatTime(kb.updated_at) }}</span>
        </div>
      </div>
    </div>

    <!-- 知识库详情抽屉 -->
    <Transition name="drawer">
      <div v-if="activeKb" class="kb-drawer">
        <div class="kb-drawer__mask" @click="activeKb = null" />
        <div class="kb-drawer__panel">
          <div class="kb-drawer__header">
            <div>
              <div class="kb-drawer__title">{{ activeKb.name }}</div>
              <div class="kb-drawer__desc">{{ activeKb.description }}</div>
            </div>
            <button class="kb-drawer__close" @click="activeKb = null">✕</button>
          </div>

          <!-- 上传区 -->
          <div class="kb-upload-zone" :class="{ 'kb-upload-zone--active': dragOver }"
            @dragover.prevent="dragOver = true" @dragleave="dragOver = false"
            @drop.prevent="onDrop" @click="fileInputRef?.click()">
            <input ref="fileInputRef" type="file" style="display:none" multiple
              accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.mp4,.avi,.mov"
              @change="onFileChange" />
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style="color:#94a3b8"><path d="M12 16V8M8 12l4-4 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.5"/></svg>
            <span class="kb-upload-hint">{{ uploading ? '上传中...' : '点击或拖拽文件上传（支持多文件）' }}</span>
            <span class="kb-upload-types">PDF / Word / Excel / 图片 / 视频</span>
          </div>

          <!-- 文件列表 -->
          <div class="kb-file-list">
            <div v-if="!activeKb.files?.length" class="kb-file-empty">暂无文件</div>
            <div v-for="f in activeKb.files" :key="f.id" class="kb-file-item"
              :class="{ 'kb-file-item--active': activeFile?.id === f.id }"
              @click="toggleFile(f)">
              <span class="kb-file-icon">{{ fileIcon(f.file_type) }}</span>
              <div class="kb-file-info">
                <div class="kb-file-name">{{ f.name }}</div>
                <div class="kb-file-meta">{{ formatSize(f.size) }} · {{ f.file_type }}</div>
              </div>
              <div class="kb-file-actions" @click.stop>
                <button v-if="f.has_content" class="kb-icon-btn" @click="toggleFile(f)" title="预览">
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" stroke="currentColor" stroke-width="1.5"/></svg>
                </button>
                <button class="kb-icon-btn kb-icon-btn--danger" @click="handleDeleteFile(f)" title="删除">
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 10h8l1-10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
              </div>
            </div>
          </div>

          <!-- 文件内容预览 -->
          <Transition name="content-slide">
            <div v-if="activeFile && fileContent" class="kb-content-preview">
              <div class="kb-content-header">
                <span>{{ activeFile.name }} — 解析内容</span>
                <button class="kb-icon-btn" @click="activeFile = null; fileContent = ''">✕</button>
              </div>
              <pre class="kb-content-pre">{{ fileContent }}</pre>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>

    <!-- 新建/编辑弹窗 -->
    <div v-if="showForm" class="kb-dialog-mask" @click.self="showForm = false">
      <div class="kb-dialog">
        <div class="kb-dialog__title">{{ editingKb ? '编辑知识库' : '新建知识库' }}</div>
        <div class="kb-form-field">
          <label>名称 <span style="color:#ef4444">*</span></label>
          <input v-model="formData.name" class="kb-form-input" placeholder="如：产品手册库" />
        </div>
        <div class="kb-form-field">
          <label>描述</label>
          <textarea v-model="formData.description" class="kb-form-input kb-form-ta" rows="2" placeholder="可选"></textarea>
        </div>
        <div class="kb-form-field">
          <label>标签（逗号分隔）</label>
          <input v-model="formData.tags" class="kb-form-input" placeholder="如：产品,文档,2024" />
        </div>
        <div class="kb-dialog__footer">
          <button class="btn-secondary" @click="showForm = false">取消</button>
          <button class="btn-primary" :disabled="saving || !formData.name" @click="handleSave">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '../../api/knowledge'
import type { KnowledgeBase, KnowledgeFile, SearchResult } from '../../api/knowledge'

const kbs = ref<KnowledgeBase[]>([])
const loading = ref(false)
const activeKb = ref<KnowledgeBase | null>(null)
const activeFile = ref<KnowledgeFile | null>(null)
const fileContent = ref('')
const dragOver = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const searchQ = ref('')
const lastSearchQ = ref('')
const searchResults = ref<SearchResult[]>([])
const showForm = ref(false)
const saving = ref(false)
const editingKb = ref<KnowledgeBase | null>(null)
const formData = ref({ name: '', description: '', tags: '' })

onMounted(loadKbs)

async function loadKbs() {
  loading.value = true
  try { kbs.value = await knowledgeApi.list() } finally { loading.value = false }
}

async function openKb(kb: KnowledgeBase) {
  const detail = await knowledgeApi.get(kb.id)
  activeKb.value = detail
  activeFile.value = null
  fileContent.value = ''
}

async function openKbById(kbId: string) {
  const detail = await knowledgeApi.get(kbId)
  activeKb.value = detail
  activeFile.value = null
  fileContent.value = ''
}

async function toggleFile(f: KnowledgeFile) {
  if (activeFile.value?.id === f.id) { activeFile.value = null; fileContent.value = ''; return }
  if (!f.has_content) return
  activeFile.value = f
  fileContent.value = '加载中...'
  const res = await knowledgeApi.getFileContent(f.kb_id, f.id)
  fileContent.value = res.content || '（无解析内容）'
}

async function onDrop(e: DragEvent) {
  dragOver.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  for (const f of files) await uploadOne(f)
}

async function onFileChange(e: Event) {
  const files = Array.from((e.target as HTMLInputElement).files || [])
  for (const f of files) await uploadOne(f)
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function uploadOne(file: File) {
  if (!activeKb.value) return
  uploading.value = true
  try {
    const kf = await knowledgeApi.uploadFile(activeKb.value.id, file)
    activeKb.value.files = [kf, ...(activeKb.value.files || [])]
    const kb = kbs.value.find(k => k.id === activeKb.value!.id)
    if (kb) kb.file_count++
  } catch (e: any) {
    alert(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleDeleteFile(f: KnowledgeFile) {
  if (!confirm(`确认删除文件「${f.name}」？`)) return
  await knowledgeApi.deleteFile(f.kb_id, f.id)
  if (activeKb.value) {
    activeKb.value.files = activeKb.value.files?.filter(x => x.id !== f.id)
    const kb = kbs.value.find(k => k.id === f.kb_id)
    if (kb) kb.file_count = Math.max(0, kb.file_count - 1)
  }
  if (activeFile.value?.id === f.id) { activeFile.value = null; fileContent.value = '' }
}

async function handleDelete(kb: KnowledgeBase) {
  if (!confirm(`确认删除知识库「${kb.name}」及其所有文件？`)) return
  await knowledgeApi.delete(kb.id)
  kbs.value = kbs.value.filter(k => k.id !== kb.id)
  if (activeKb.value?.id === kb.id) activeKb.value = null
}

function openCreate() {
  editingKb.value = null
  formData.value = { name: '', description: '', tags: '' }
  showForm.value = true
}

function openEdit(kb: KnowledgeBase) {
  editingKb.value = kb
  formData.value = { name: kb.name, description: kb.description, tags: kb.tags.join(', ') }
  showForm.value = true
}

async function handleSave() {
  if (!formData.value.name) return
  saving.value = true
  try {
    if (editingKb.value) {
      const updated = await knowledgeApi.update(editingKb.value.id, formData.value.name, formData.value.description, formData.value.tags)
      const idx = kbs.value.findIndex(k => k.id === editingKb.value!.id)
      if (idx >= 0) kbs.value[idx] = { ...kbs.value[idx], ...updated }
      if (activeKb.value?.id === editingKb.value.id) activeKb.value = { ...activeKb.value, ...updated }
    } else {
      const kb = await knowledgeApi.create(formData.value.name, formData.value.description, formData.value.tags)
      kbs.value.unshift(kb)
    }
    showForm.value = false
  } catch (e: any) {
    alert(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function doSearch() {
  if (!searchQ.value.trim()) return
  lastSearchQ.value = searchQ.value
  searchResults.value = await knowledgeApi.search(searchQ.value)
}

function clearSearch() { searchResults.value = []; searchQ.value = ''; lastSearchQ.value = '' }

function fileIcon(type: string) {
  const m: Record<string, string> = { pdf: '📄', word: '📝', excel: '📊', image: '🖼', video: '🎬' }
  return m[type] || '📁'
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.kb-page { padding: 28px 32px; max-width: 1200px; }
.kb-page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.kb-header-right { display: flex; align-items: center; gap: 10px; }
.kb-search-wrap { position: relative; display: flex; align-items: center; }
.kb-search-icon { position: absolute; left: 10px; color: var(--neutral-400); }
.kb-search { padding: 8px 12px 8px 32px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 13px; width: 220px; color: var(--neutral-800); background: var(--neutral-0); outline: none; }
.kb-search:focus { border-color: var(--semantic-500); }

.kb-search-results { margin-bottom: 20px; border: 1px solid var(--neutral-100); border-radius: var(--radius-lg); overflow: hidden; }
.kb-search-results__header { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: var(--neutral-50); font-size: 12px; color: var(--neutral-600); border-bottom: 1px solid var(--neutral-100); }
.kb-clear-search { font-size: 11px; color: var(--semantic-500); background: none; border: none; cursor: pointer; }
.kb-search-item { padding: 10px 16px; border-bottom: 1px solid var(--neutral-50); cursor: pointer; transition: background .12s; }
.kb-search-item:hover { background: var(--neutral-50); }
.kb-search-item__kb { font-size: 10px; font-weight: 600; color: var(--semantic-500); text-transform: uppercase; letter-spacing: .04em; }
.kb-search-item__file { font-size: 13px; font-weight: 500; color: var(--neutral-800); margin: 2px 0; }
.kb-search-item__snippet { font-size: 12px; color: var(--neutral-500); }

.kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.kb-empty { grid-column: 1/-1; display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 60px 20px; color: var(--neutral-400); font-size: 13px; }

.kb-card {
  border: 1px solid var(--neutral-100); border-radius: var(--radius-lg);
  padding: 16px; cursor: pointer; transition: all .15s; background: var(--neutral-0);
  display: flex; flex-direction: column; gap: 8px;
}
.kb-card:hover { border-color: var(--semantic-300); box-shadow: 0 4px 16px rgba(0,0,0,.06); transform: translateY(-1px); }
.kb-card__header { display: flex; justify-content: space-between; align-items: flex-start; }
.kb-card__icon { color: var(--semantic-500); }
.kb-card__actions { display: flex; gap: 4px; opacity: 0; transition: opacity .15s; }
.kb-card:hover .kb-card__actions { opacity: 1; }
.kb-card__name { font-size: 14px; font-weight: 700; color: var(--neutral-900); }
.kb-card__desc { font-size: 12px; color: var(--neutral-500); line-height: 1.5; flex: 1; }
.kb-card__tags { display: flex; flex-wrap: wrap; gap: 4px; }
.kb-tag { font-size: 10px; padding: 2px 7px; border-radius: 10px; background: var(--semantic-50, #eff6ff); color: var(--semantic-600, #2563eb); font-weight: 500; }
.kb-card__footer { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--neutral-400); margin-top: 4px; }
.kb-card__count { font-weight: 600; color: var(--neutral-600); }

.kb-icon-btn { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 5px; border: none; background: transparent; color: var(--neutral-400); cursor: pointer; transition: all .12s; }
.kb-icon-btn:hover { background: var(--neutral-100); color: var(--neutral-700); }
.kb-icon-btn--danger:hover { background: #fee2e2; color: #ef4444; }

/* 抽屉 */
.kb-drawer { position: fixed; inset: 0; z-index: 400; }
.kb-drawer__mask { position: absolute; inset: 0; background: rgba(0,0,0,.25); }
.kb-drawer__panel {
  position: absolute; right: 0; top: 0; bottom: 0; width: 420px;
  background: var(--neutral-0); border-left: 1px solid var(--neutral-100);
  display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(0,0,0,.08);
  overflow: hidden;
}
.kb-drawer__header { display: flex; justify-content: space-between; align-items: flex-start; padding: 20px; border-bottom: 1px solid var(--neutral-100); flex-shrink: 0; }
.kb-drawer__title { font-size: 15px; font-weight: 700; color: var(--neutral-900); }
.kb-drawer__desc { font-size: 12px; color: var(--neutral-500); margin-top: 3px; }
.kb-drawer__close { background: none; border: none; cursor: pointer; font-size: 16px; color: var(--neutral-400); padding: 2px 6px; border-radius: 4px; }
.kb-drawer__close:hover { background: var(--neutral-100); }

.kb-upload-zone {
  margin: 12px 16px; border: 2px dashed var(--neutral-200); border-radius: var(--radius-lg);
  padding: 16px; text-align: center; cursor: pointer; transition: all .15s;
  display: flex; flex-direction: column; align-items: center; gap: 4px; flex-shrink: 0;
}
.kb-upload-zone--active { border-color: var(--semantic-400); background: var(--semantic-50, #eff6ff); }
.kb-upload-zone:hover { border-color: var(--semantic-300); }
.kb-upload-hint { font-size: 12px; color: var(--neutral-600); }
.kb-upload-types { font-size: 10px; color: var(--neutral-400); }

.kb-file-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.kb-file-empty { padding: 24px 16px; text-align: center; font-size: 12px; color: var(--neutral-400); }
.kb-file-item { display: flex; align-items: center; gap: 10px; padding: 10px 16px; cursor: pointer; transition: background .12s; border-bottom: 1px solid var(--neutral-50); }
.kb-file-item:hover { background: var(--neutral-50); }
.kb-file-item--active { background: var(--semantic-50, #eff6ff); }
.kb-file-icon { font-size: 20px; flex-shrink: 0; }
.kb-file-info { flex: 1; min-width: 0; }
.kb-file-name { font-size: 13px; font-weight: 500; color: var(--neutral-800); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kb-file-meta { font-size: 11px; color: var(--neutral-400); margin-top: 2px; }
.kb-file-actions { display: flex; gap: 2px; opacity: 0; transition: opacity .12s; flex-shrink: 0; }
.kb-file-item:hover .kb-file-actions { opacity: 1; }

.kb-content-preview { border-top: 1px solid var(--neutral-100); max-height: 280px; display: flex; flex-direction: column; flex-shrink: 0; }
.kb-content-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; font-size: 11px; font-weight: 600; color: var(--neutral-600); background: var(--neutral-50); border-bottom: 1px solid var(--neutral-100); flex-shrink: 0; }
.kb-content-pre { flex: 1; overflow-y: auto; padding: 12px 16px; font-size: 11px; font-family: 'Consolas', monospace; white-space: pre-wrap; word-break: break-all; color: var(--neutral-700); line-height: 1.6; margin: 0; }

/* 弹窗 */
.kb-dialog-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 500; }
.kb-dialog { background: var(--neutral-0); border-radius: var(--radius-xl); padding: 24px; width: 400px; display: flex; flex-direction: column; gap: 14px; box-shadow: 0 20px 60px rgba(0,0,0,.15); }
.kb-dialog__title { font-size: 15px; font-weight: 700; color: var(--neutral-900); }
.kb-form-field { display: flex; flex-direction: column; gap: 5px; }
.kb-form-field label { font-size: 11px; font-weight: 600; color: var(--neutral-600); }
.kb-form-input { padding: 7px 10px; border-radius: var(--radius-md); font-size: 13px; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-800); outline: none; width: 100%; box-sizing: border-box; font-family: inherit; }
.kb-form-input:focus { border-color: var(--semantic-500); }
.kb-form-ta { resize: vertical; min-height: 60px; }
.kb-dialog__footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }

/* 过渡 */
.drawer-enter-active, .drawer-leave-active { transition: all .2s ease; }
.drawer-enter-from .kb-drawer__panel, .drawer-leave-to .kb-drawer__panel { transform: translateX(100%); }
.drawer-enter-from .kb-drawer__mask, .drawer-leave-to .kb-drawer__mask { opacity: 0; }
.content-slide-enter-active, .content-slide-leave-active { transition: all .2s ease; }
.content-slide-enter-from, .content-slide-leave-to { transform: translateY(10px); opacity: 0; }
</style>
