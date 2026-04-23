<template>
  <div class="agents-page">
    <div class="agents-topbar">
      <div class="agents-topbar__left">
        <span class="agents-title">智能体管理</span>
        <span class="agents-count">{{ filtered.length }} 个智能体</span>
      </div>
      <div class="agents-topbar__right">
        <div class="agents-search">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.5"/><path d="M10.5 10.5l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <input v-model="search" placeholder="搜索智能体..." class="agents-search__input" />
        </div>
        <button class="btn btn--primary" @click="goCreate">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          新建智能体
        </button>
      </div>
    </div>

    <div class="agents-body">
      <div v-if="loading" class="agents-loading">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>

      <div v-else-if="filtered.length === 0" class="agents-empty">
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none" opacity=".25"><path d="M28 8a20 20 0 100 40A20 20 0 0028 8z" stroke="currentColor" stroke-width="2"/><path d="M20 24c0-4.4 3.6-8 8-8s8 3.6 8 8v4H20v-4z" stroke="currentColor" stroke-width="2"/><rect x="16" y="28" width="24" height="16" rx="3" stroke="currentColor" stroke-width="2"/></svg>
        <p>暂无智能体，点击「新建智能体」开始创建</p>
      </div>

      <div v-else class="agents-grid">
        <div v-for="a in filtered" :key="a.id" class="agent-card" @click="goEdit(a)">
          <div class="agent-card__header">
            <div class="agent-card__avatar">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 2a5 5 0 100 10A5 5 0 0012 2z" stroke="currentColor" stroke-width="1.8"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="19" cy="8" r="2" fill="currentColor" opacity=".4"/><circle cx="5" cy="8" r="2" fill="currentColor" opacity=".4"/></svg>
            </div>
            <div class="agent-card__meta">
              <span class="agent-card__name">{{ a.name }}</span>
              <span class="agent-card__badge" :class="a.status === 'published' ? 'badge--green' : 'badge--gray'">
                {{ a.status === 'published' ? '已发布' : '草稿' }}
              </span>
            </div>
          </div>

          <p class="agent-card__desc">{{ a.description || '暂无描述' }}</p>

          <div class="agent-card__tags" v-if="a.tags?.length">
            <span v-for="t in a.tags.slice(0, 3)" :key="t" class="tag">{{ t }}</span>
          </div>

          <div class="agent-card__footer">
            <span class="agent-card__model">
              <svg width="11" height="11" viewBox="0 0 16 16" fill="none"><rect x="2" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="10" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M6 8h4" stroke="currentColor" stroke-width="1.5"/></svg>
              {{ a.model_name || '默认模型' }}
            </span>
            <div class="agent-card__actions">
              <button class="btn-icon" title="编辑" @click.stop="goEdit(a)">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
              </button>
              <button class="btn-icon btn-icon--danger" title="删除" @click.stop="confirmDelete(a)">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 5h10M6 5V3h4v2M6 8v5M10 8v5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="deleteTarget" class="modal-mask" @click.self="deleteTarget = null">
      <div class="modal">
        <div class="modal__title">确认删除</div>
        <p class="modal__body">确定要删除智能体「{{ deleteTarget.name }}」吗？此操作不可撤销。</p>
        <div class="modal__footer">
          <button class="btn btn--ghost" @click="deleteTarget = null">取消</button>
          <button class="btn btn--danger" :disabled="deleting" @click="doDelete">{{ deleting ? '删除中...' : '确认删除' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { agentsApi, type AgentItem } from '../../api/agents'

const router = useRouter()
const agents = ref<AgentItem[]>([])
const loading = ref(true)
const search = ref('')
const deleteTarget = ref<AgentItem | null>(null)
const deleting = ref(false)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return agents.value
  return agents.value.filter(a =>
    a.name.toLowerCase().includes(q) ||
    a.description?.toLowerCase().includes(q) ||
    a.tags?.some(t => t.toLowerCase().includes(q))
  )
})

async function load() {
  loading.value = true
  try {
    agents.value = await agentsApi.list()
  } catch (e) {
    console.error('加载智能体失败', e)
  } finally {
    loading.value = false
  }
}

const creating = ref(false)

async function goCreate() {
  if (creating.value) return
  creating.value = true
  try {
    const agent = await agentsApi.create({ name: '未命名智能体' })
    router.push(`/agents/${agent.id}`)
  } catch (e) {
    console.error('创建智能体失败', e)
  } finally {
    creating.value = false
  }
}

function goEdit(a: AgentItem) {
  router.push(`/agents/${a.id}`)
}

function confirmDelete(a: AgentItem) {
  deleteTarget.value = a
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await agentsApi.delete(deleteTarget.value.id)
    deleteTarget.value = null
    await load()
  } catch (e) {
    console.error('删除失败', e)
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.agents-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--neutral-50, #f5f7fa);
  overflow: hidden;
}

.agents-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--neutral-0, #fff);
  border-bottom: 1px solid var(--neutral-200, #e8e8e8);
  flex-shrink: 0;
}

.agents-topbar__left { display: flex; align-items: center; gap: 10px; }
.agents-title { font-size: 16px; font-weight: 700; color: var(--neutral-900, #1a1a2e); }
.agents-count { font-size: 12px; color: var(--neutral-400, #999); background: var(--neutral-100, #f0f0f0); padding: 2px 8px; border-radius: 10px; }

.agents-topbar__right { display: flex; align-items: center; gap: 10px; }

.agents-search {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--neutral-100, #f5f5f5);
  border: 1px solid var(--neutral-200, #e8e8e8);
  border-radius: 6px;
  padding: 5px 10px;
  color: var(--neutral-400, #999);
}
.agents-search__input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  color: var(--neutral-800, #333);
  width: 180px;
}
.agents-search__input::placeholder { color: var(--neutral-400, #bbb); }

.btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}
.btn--primary { background: var(--semantic-500, #4c6ef5); color: #fff; border-color: var(--semantic-500, #4c6ef5); }
.btn--primary:hover { background: var(--semantic-600, #3b5bdb); }
.btn--ghost { background: transparent; color: var(--neutral-600, #555); border-color: var(--neutral-300, #d9d9d9); }
.btn--ghost:hover { background: var(--neutral-100, #f5f5f5); }
.btn--danger { background: #ff4d4f; color: #fff; border-color: #ff4d4f; }
.btn--danger:hover { background: #d9363e; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.agents-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.agents-loading, .agents-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 12px;
  color: var(--neutral-400, #999);
  font-size: 14px;
}

.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--neutral-200, #e8e8e8);
  border-top-color: var(--semantic-500, #4c6ef5);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.agent-card {
  background: #fff;
  border: 1px solid var(--neutral-200, #e8e8e8);
  border-radius: 10px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow 0.15s, border-color 0.15s;
  cursor: default;
}
.agent-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  border-color: var(--semantic-300, #a5b4fc);
}

.agent-card__header { display: flex; align-items: center; gap: 10px; }
.agent-card__avatar {
  width: 40px; height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  display: flex; align-items: center; justify-content: center;
  color: var(--semantic-600, #3b5bdb);
  flex-shrink: 0;
}
.agent-card__meta { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.agent-card__name { font-size: 14px; font-weight: 600; color: var(--neutral-900, #1a1a2e); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.agent-card__badge {
  display: inline-block;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 10px;
  font-weight: 500;
  width: fit-content;
}
.badge--green { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.badge--gray { background: #f5f5f5; color: #888; border: 1px solid #e0e0e0; }

.agent-card__desc {
  font-size: 12px;
  color: var(--neutral-500, #777);
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.agent-card__tags { display: flex; flex-wrap: wrap; gap: 5px; }
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--neutral-100, #f0f0f0);
  color: var(--neutral-600, #555);
}

.agent-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--neutral-100, #f0f0f0);
}
.agent-card__model {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--neutral-400, #aaa);
}
.agent-card__actions { display: flex; gap: 4px; }

.btn-icon {
  width: 28px; height: 28px;
  border-radius: 6px;
  border: 1px solid var(--neutral-200, #e8e8e8);
  background: transparent;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--neutral-500, #777);
  transition: all 0.15s;
}
.btn-icon:hover { background: var(--neutral-100, #f5f5f5); color: var(--semantic-500, #4c6ef5); border-color: var(--semantic-300, #a5b4fc); }
.btn-icon--danger:hover { background: #fff1f0; color: #ff4d4f; border-color: #ffccc7; }

.modal-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  width: 360px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.modal__title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin-bottom: 10px; }
.modal__body { font-size: 13px; color: #555; margin: 0 0 20px; line-height: 1.6; }
.modal__footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
