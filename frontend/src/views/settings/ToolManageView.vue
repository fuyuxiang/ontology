<template>
  <div class="tool-manage">
    <div class="tool-manage__header">
      <div>
        <h1 class="page-title">工具管理</h1>
        <p class="page-desc">注册和管理 Agent 可调用的工具，包括内置工具和自定义工具</p>
      </div>
      <button class="btn-primary" @click="showForm = true">+ 注册工具</button>
    </div>

    <div class="tool-list">
      <div v-for="tool in tools" :key="tool.id" class="tool-card">
        <div class="tool-card__icon">
          <svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M10 2a3 3 0 00-2.83 4L3 10.17V13h2.83L10 8.83A3 3 0 1010 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
        </div>
        <div class="tool-card__info">
          <div class="tool-card__name">{{ tool.name }}</div>
          <div class="tool-card__desc">{{ tool.description }}</div>
          <div class="tool-card__meta">
            <span class="tool-card__type">{{ tool.tool_type === 'builtin' ? '内置' : '自定义' }}</span>
            <span class="tool-card__params">{{ tool.param_count }} 个参数</span>
          </div>
        </div>
        <div class="tool-card__actions">
          <button class="btn-icon" @click="editTool(tool)" title="编辑">✏️</button>
          <button class="btn-icon" @click="deleteTool(tool.id)" title="删除" v-if="tool.tool_type !== 'builtin'">🗑️</button>
        </div>
      </div>
      <div v-if="tools.length === 0" class="tool-list__empty">暂无工具，点击"注册工具"添加</div>
    </div>

    <!-- 注册/编辑表单 -->
    <div v-if="showForm" class="form-overlay" @click.self="showForm = false">
      <div class="form-drawer">
        <h3 class="form-title">{{ editingId ? '编辑工具' : '注册工具' }}</h3>
        <div class="form-body">
          <div class="form-row">
            <label class="form-label">工具名称</label>
            <input v-model="form.name" class="form-input" placeholder="如：query_database" />
          </div>
          <div class="form-row">
            <label class="form-label">描述</label>
            <textarea v-model="form.description" class="form-input" rows="2" placeholder="工具功能描述"></textarea>
          </div>
          <div class="form-row">
            <label class="form-label">参数 Schema (JSON)</label>
            <textarea v-model="form.params_schema" class="form-input form-input--code" rows="6" placeholder='{"type":"object","properties":{}}'></textarea>
          </div>
          <div class="form-row">
            <label class="form-label">执行方式</label>
            <select v-model="form.execution_type" class="form-input">
              <option value="http">HTTP 调用</option>
              <option value="python">Python 函数</option>
              <option value="sql">SQL 查询</option>
            </select>
          </div>
          <div class="form-row" v-if="form.execution_type === 'http'">
            <label class="form-label">端点 URL</label>
            <input v-model="form.endpoint_url" class="form-input" placeholder="https://..." />
          </div>
        </div>
        <div class="form-actions">
          <button class="btn-secondary" @click="showForm = false">取消</button>
          <button class="btn-primary" @click="saveTool">{{ editingId ? '保存' : '创建' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { get, post } from '../../api/client'

interface Tool { id: string; name: string; description: string; tool_type: string; param_count: number }

const tools = ref<Tool[]>([])
const showForm = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', description: '', params_schema: '', execution_type: 'http', endpoint_url: '' })

function resetForm() {
  form.name = ''; form.description = ''; form.params_schema = ''; form.execution_type = 'http'; form.endpoint_url = ''
  editingId.value = null
}

function editTool(tool: Tool) {
  editingId.value = tool.id
  form.name = tool.name
  form.description = tool.description
  showForm.value = true
}

async function saveTool() {
  showForm.value = false
  resetForm()
  await loadTools()
}

async function deleteTool(id: string) {
  if (!confirm('确定删除该工具？')) return
  try {
    await post(`/tools/${id}/delete`, {})
    await loadTools()
  } catch { /* ignore */ }
}

async function loadTools() {
  try {
    const data = await get<Tool[]>('/tools')
    tools.value = data
  } catch {
    tools.value = [
      { id: '1', name: 'describe_ontology_model', description: '获取本体模型概览', tool_type: 'builtin', param_count: 0 },
      { id: '2', name: 'query_datasource', description: '执行数据源 SQL 查询', tool_type: 'builtin', param_count: 2 },
      { id: '3', name: 'get_entity_detail', description: '获取实体详细信息', tool_type: 'builtin', param_count: 1 },
      { id: '4', name: 'query_entity_data', description: '查询实体实例数据', tool_type: 'builtin', param_count: 3 },
    ]
  }
}

onMounted(loadTools)
</script>

<style scoped>
.tool-manage { padding: 20px 24px; }
.tool-manage__header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 0; }

.tool-list { display: flex; flex-direction: column; gap: 8px; }
.tool-card { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border: 1px solid var(--neutral-200); border-radius: 10px; background: var(--neutral-0); }
.tool-card:hover { border-color: var(--neutral-300); box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
.tool-card__icon { width: 36px; height: 36px; border-radius: 8px; background: var(--neutral-100); display: flex; align-items: center; justify-content: center; color: var(--neutral-500); flex-shrink: 0; }
.tool-card__info { flex: 1; min-width: 0; }
.tool-card__name { font-size: 13px; font-weight: 600; color: var(--neutral-800); font-family: monospace; }
.tool-card__desc { font-size: 12px; color: var(--neutral-500); margin-top: 2px; }
.tool-card__meta { display: flex; gap: 8px; margin-top: 4px; }
.tool-card__type { font-size: 10px; padding: 1px 6px; border-radius: 4px; background: var(--neutral-100); color: var(--neutral-600); }
.tool-card__params { font-size: 10px; color: var(--neutral-400); }
.tool-card__actions { display: flex; gap: 4px; }
.btn-icon { background: none; border: none; cursor: pointer; font-size: 14px; padding: 4px; border-radius: 4px; }
.btn-icon:hover { background: var(--neutral-100); }
.tool-list__empty { text-align: center; padding: 40px; color: var(--neutral-400); font-size: 13px; }

.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.form-drawer { background: #fff; border-radius: 12px; width: 480px; max-height: 80vh; overflow-y: auto; padding: 24px; box-shadow: 0 16px 48px rgba(0,0,0,0.15); }
.form-title { font-size: 16px; font-weight: 700; margin: 0 0 16px; color: var(--neutral-900); }
.form-body { display: flex; flex-direction: column; gap: 12px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 12px; font-weight: 600; color: var(--neutral-600); }
.form-input { padding: 7px 10px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 13px; outline: none; font-family: inherit; }
.form-input:focus { border-color: var(--semantic-500); }
.form-input--code { font-family: monospace; font-size: 11px; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.btn-primary { padding: 8px 16px; border-radius: 6px; border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: var(--semantic-700); }
.btn-secondary { padding: 8px 16px; border-radius: 6px; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); font-size: 13px; cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50); }
</style>
