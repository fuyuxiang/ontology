<template>
  <div class="pt-page">
    <!-- 顶部 -->
    <div class="pt-page__top">
      <div>
        <h1 class="pt-page__title">Prompt 模板</h1>
        <p class="pt-page__subtitle">管理可复用的提示词模板，供智能体创建时选用</p>
      </div>
      <a-button type="primary" size="small" @click="openCreate">+ 新建模板</a-button>
    </div>

    <!-- 分类过滤 -->
    <div class="pt-cats">
      <span
        v-for="cat in categories"
        :key="cat"
        class="pt-cat"
        :class="{ 'pt-cat--active': activeCategory === cat }"
        @click="activeCategory = cat"
      >{{ cat }}</span>
    </div>

    <PageState :loading="loading" :empty="!loading && filtered.length === 0" empty-text="暂无模板">
      <div class="pt-grid">
        <div v-for="t in filtered" :key="t.id" class="pt-card" @click="openDetail(t)">
          <div class="pt-card__head">
            <span class="pt-card__cat" :class="`cat-${t.category}`">{{ t.category }}</span>
            <div class="pt-card__actions" @click.stop>
              <a-button size="small" @click="openEdit(t)">编辑</a-button>
              <a-popconfirm title="确认删除？" @confirm="doDelete(t.id)">
                <a-button size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
          </div>
          <h3 class="pt-card__name">{{ t.name }}</h3>
          <p class="pt-card__desc">{{ t.description }}</p>
          <div class="pt-card__tags">
            <span v-for="tag in (t.tags || [])" :key="tag" class="pt-tag">{{ tag }}</span>
          </div>
          <div class="pt-card__footer">
            <span class="pt-card__vars" v-if="t.variables?.length">{{ t.variables.length }} 个变量</span>
            <span class="pt-card__time">{{ fmt(t.updated_at) }}</span>
          </div>
        </div>
      </div>
    </PageState>

    <!-- 详情抽屉 -->
    <a-drawer v-model:open="detailOpen" :title="selected?.name" width="600" placement="right">
      <template v-if="selected">
        <div class="detail-meta">
          <span class="pt-card__cat" :class="`cat-${selected.category}`">{{ selected.category }}</span>
          <span class="pt-card__time">更新于 {{ fmt(selected.updated_at) }}</span>
        </div>
        <p class="detail-desc">{{ selected.description }}</p>

        <div v-if="selected.variables?.length" class="detail-vars">
          <h4>变量</h4>
          <table class="vars-table">
            <thead><tr><th>变量名</th><th>说明</th><th>默认值</th></tr></thead>
            <tbody>
              <tr v-for="v in selected.variables" :key="v.name">
                <td><code>{{ '{' + '{' + v.name + '}' + '}' }}</code></td>
                <td>{{ v.description }}</td>
                <td>{{ v.default || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="detail-content">
          <h4>模板内容</h4>
          <pre class="detail-pre">{{ selected.content }}</pre>
        </div>
      </template>
    </a-drawer>

    <!-- 新建/编辑弹窗 -->
    <a-modal
      v-model:open="formOpen"
      :title="editingId ? '编辑模板' : '新建模板'"
      width="700"
      @ok="doSave"
      :confirm-loading="saving"
      ok-text="保存"
      cancel-text="取消"
    >
      <div class="form-grid">
        <div class="form-row">
          <label>模板名称 <span class="form-required">*</span></label>
          <a-input v-model:value="form.name" placeholder="如：宽带退单稽核智能体" />
        </div>
        <div class="form-row">
          <label>分类</label>
          <a-select v-model:value="form.category" style="width:100%">
            <a-select-option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</a-select-option>
          </a-select>
        </div>
        <div class="form-row">
          <label>描述</label>
          <a-input v-model:value="form.description" placeholder="简要描述模板用途" />
        </div>
        <div class="form-row">
          <label>标签（逗号分隔）</label>
          <a-input v-model:value="tagsInput" placeholder="如：宽带,退单,稽核" />
        </div>
        <div class="form-row form-row--full">
          <label>模板内容 <span class="form-required">*</span></label>
          <a-textarea v-model:value="form.content" :rows="12" placeholder="输入提示词内容，可使用 {{变量名}} 占位符" />
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import PageState from '../../components/common/PageState.vue'
import { get, post, put, del } from '../../api/client'

interface PromptTemplate {
  id: string
  name: string
  description: string
  category: string
  content: string
  variables: { name: string; description: string; default: string }[] | null
  tags: string[] | null
  status: string
  created_at: string
  updated_at: string
}

const loading = ref(true)
const templates = ref<PromptTemplate[]>([])
const activeCategory = ref('全部')
const detailOpen = ref(false)
const formOpen = ref(false)
const saving = ref(false)
const selected = ref<PromptTemplate | null>(null)
const editingId = ref<string | null>(null)
const tagsInput = ref('')

const categoryOptions = ['通用', '稽核', '预警', '根因', '续约']
const categories = computed(() => ['全部', ...categoryOptions])

const form = reactive({ name: '', description: '', category: '通用', content: '' })

const filtered = computed(() =>
  activeCategory.value === '全部'
    ? templates.value
    : templates.value.filter(t => t.category === activeCategory.value),
)

function fmt(d: string) {
  return d ? d.replace('T', ' ').slice(0, 16) : '-'
}

async function fetchList() {
  loading.value = true
  try {
    templates.value = await get<PromptTemplate[]>('/prompt-templates')
  } finally {
    loading.value = false
  }
}

function openDetail(t: PromptTemplate) { selected.value = t; detailOpen.value = true }

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', description: '', category: '通用', content: '' })
  tagsInput.value = ''
  formOpen.value = true
}

function openEdit(t: PromptTemplate) {
  editingId.value = t.id
  Object.assign(form, { name: t.name, description: t.description, category: t.category, content: t.content })
  tagsInput.value = (t.tags || []).join(',')
  formOpen.value = true
}

async function doSave() {
  if (!form.name.trim() || !form.content.trim()) {
    message.warning('名称和内容不能为空')
    return
  }
  saving.value = true
  try {
    const tags = tagsInput.value ? tagsInput.value.split(',').map(s => s.trim()).filter(Boolean) : []
    // extract variables from {{varname}} placeholders
    const varMatches = [...new Set(form.content.match(/\{\{(\w+)\}\}/g)?.map(m => m.slice(2, -2)) || [])]
    const variables = varMatches.map(name => ({ name, description: '', default: '' }))
    const payload = { ...form, tags, variables, status: 'active' }
    if (editingId.value) {
      await put(`/prompt-templates/${editingId.value}`, payload)
      message.success('已更新')
    } else {
      await post('/prompt-templates', payload)
      message.success('已创建')
    }
    formOpen.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

async function doDelete(id: string) {
  await del(`/prompt-templates/${id}`)
  message.success('已删除')
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.pt-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.pt-page__top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.pt-page__title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.pt-page__subtitle { font-size: var(--text-caption-size); color: var(--neutral-500); margin: 0; }

.pt-cats { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.pt-cat { padding: 4px 14px; border-radius: 20px; font-size: var(--text-body-size); cursor: pointer; border: 1px solid var(--neutral-200); color: var(--neutral-600); transition: all 0.15s; }
.pt-cat:hover { border-color: var(--semantic-400); color: var(--semantic-600); }
.pt-cat--active { background: var(--semantic-500); border-color: var(--semantic-500); color: #fff; }

.pt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }

.pt-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 16px; cursor: pointer; transition: all 0.15s; }
.pt-card:hover { border-color: var(--semantic-300); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.pt-card__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.pt-card__actions { display: flex; gap: 6px; opacity: 0; transition: opacity 0.15s; }
.pt-card:hover .pt-card__actions { opacity: 1; }
.pt-card__name { font-size: 15px; font-weight: 600; color: var(--neutral-900); margin: 0 0 6px; }
.pt-card__desc { font-size: var(--text-caption-size); color: var(--neutral-500); margin: 0 0 10px; line-height: 1.5; }
.pt-card__tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }
.pt-card__footer { display: flex; justify-content: space-between; align-items: center; }
.pt-card__vars { font-size: 11px; color: var(--semantic-500); }
.pt-card__time { font-size: 11px; color: var(--neutral-400); }

.pt-card__cat { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 600; }
.cat-通用 { background: var(--neutral-100); color: var(--neutral-600); }
.cat-稽核 { background: var(--status-warning-bg); color: var(--kinetic-700); }
.cat-预警 { background: var(--status-error-bg); color: var(--status-error); }
.cat-根因 { background: var(--status-info-bg); color: var(--status-info); }
.cat-续约 { background: var(--status-success-bg); color: var(--status-success); }

.pt-tag { display: inline-block; padding: 1px 6px; border-radius: var(--radius-sm); font-size: 11px; background: var(--neutral-100); color: var(--neutral-500); }

/* 详情 */
.detail-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.detail-desc { font-size: var(--text-body-size); color: var(--neutral-600); margin-bottom: 16px; }
.detail-vars { margin-bottom: 16px; }
.detail-vars h4, .detail-content h4 { font-size: 14px; font-weight: 600; color: var(--neutral-700); margin: 0 0 8px; }
.vars-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-size); }
.vars-table th { text-align: left; padding: 6px 10px; background: var(--neutral-50); border-bottom: 2px solid var(--neutral-200); font-size: var(--text-caption-size); color: var(--neutral-600); }
.vars-table td { padding: 6px 10px; border-bottom: 1px solid var(--neutral-100); }
.detail-pre { background: var(--neutral-50); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); padding: 14px; font-size: var(--text-code-size); white-space: pre-wrap; word-break: break-word; color: var(--neutral-800); line-height: 1.6; max-height: 400px; overflow-y: auto; }

/* 表单 */
.form-grid { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row label { font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-700); }
.form-required { color: var(--status-error); }
</style>
