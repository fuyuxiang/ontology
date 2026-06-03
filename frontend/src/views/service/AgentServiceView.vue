<template>
  <div class="agent-manage">
    <div class="agent-manage__header">
      <div class="header-text">
        <h1 class="page-title">智能体管理</h1>
        <p class="page-desc">管理和配置智能体，作为原子能力单元供流程编排调用</p>
      </div>
      <button class="btn-primary" @click="$router.push('/agent/manage/new')">+ 新建智能体</button>
    </div>

    <div class="agent-manage__toolbar">
      <input
        v-model="searchText"
        class="search-input"
        placeholder="搜索名称或描述..."
      />
      <div class="status-filters">
        <button
          v-for="opt in statusOptions"
          :key="opt.value"
          class="filter-btn"
          :class="{ 'filter-btn--active': statusFilter === opt.value }"
          @click="statusFilter = opt.value"
        >{{ opt.label }}</button>
      </div>
    </div>

    <div v-if="filteredAgents.length" class="agent-manage__grid">
      <div
        v-for="agent in filteredAgents"
        :key="agent.id"
        class="agent-card"
        @click="$router.push(`/agent/manage/${agent.id}`)"
      >
        <div class="agent-card__top">
          <span class="agent-card__name">{{ agent.name }}</span>
          <span
            class="agent-card__badge"
            :class="agent.status === 'published' ? 'badge--published' : 'badge--draft'"
          >{{ agent.status === 'published' ? '已发布' : '草稿' }}</span>
        </div>
        <p class="agent-card__desc">{{ agent.description || '暂无描述' }}</p>
        <div v-if="agent.tags && agent.tags.length" class="agent-card__tags">
          <span v-for="tag in agent.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
        <div class="agent-card__footer">
          <span
            class="ref-count"
            :title="refsTooltip(agent)"
          >被 {{ agent.referenced_scenes?.length || 0 }} 个场景引用</span>
          <button class="btn-delete" @click.stop="confirmDelete(agent)">删除</button>
        </div>
      </div>
    </div>

    <div v-else class="agent-manage__empty">
      <p>{{ agents.length === 0 ? '暂无智能体，点击右上角新建' : '没有匹配的智能体' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { agentsApi, type AgentItem } from '../../api/agents'

const searchText = ref('')
const statusFilter = ref('all')
const agents = ref<AgentItem[]>([])

const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
]

const filteredAgents = computed(() => {
  let list = agents.value
  if (statusFilter.value !== 'all') {
    list = list.filter(a => a.status === statusFilter.value)
  }
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(a =>
      a.name.toLowerCase().includes(q) ||
      (a.description && a.description.toLowerCase().includes(q))
    )
  }
  return list
})

function refsTooltip(agent: AgentItem): string {
  if (!agent.referenced_scenes || agent.referenced_scenes.length === 0) return '未被引用'
  return agent.referenced_scenes.map(s => s.name).join('、')
}

async function confirmDelete(agent: AgentItem) {
  const refCount = agent.referenced_scenes?.length || 0
  const warning = refCount > 0
    ? `该智能体被 ${refCount} 个场景引用，删除后相关场景将受到影响。确定删除「${agent.name}」吗？`
    : `确定删除智能体「${agent.name}」吗？`
  if (!confirm(warning)) return
  try {
    await agentsApi.delete(agent.id)
    agents.value = agents.value.filter(a => a.id !== agent.id)
  } catch (e: any) {
    alert('删除失败: ' + (e.message || '未知错误'))
  }
}

async function loadAgents() {
  try {
    agents.value = await agentsApi.list()
  } catch { /* empty */ }
}

onMounted(loadAgents)
</script>

<style scoped>
.agent-manage {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  overflow-y: auto;
}

.agent-manage__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--neutral-900);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 13px;
  color: var(--neutral-500);
  margin: 0;
}

.btn-primary {
  padding: 8px 16px;
  background: var(--semantic-600);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.btn-primary:hover {
  background: var(--semantic-700);
}

.agent-manage__toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  max-width: 320px;
  padding: 8px 12px;
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}

.search-input:focus {
  border-color: var(--semantic-500);
}

.status-filters {
  display: flex;
  gap: 4px;
}

.filter-btn {
  padding: 6px 12px;
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  background: var(--neutral-0);
  font-size: 12px;
  color: var(--neutral-600);
  cursor: pointer;
}

.filter-btn:hover {
  background: var(--neutral-50);
}

.filter-btn--active {
  background: var(--semantic-50);
  border-color: var(--semantic-300);
  color: var(--semantic-700);
  font-weight: 500;
}

.agent-manage__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.agent-card {
  border: 1px solid var(--neutral-200);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-card:hover {
  border-color: var(--semantic-300);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.agent-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.agent-card__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--neutral-800);
}

.agent-card__badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.badge--published {
  background: #d1fae5;
  color: #059669;
}

.badge--draft {
  background: var(--neutral-100);
  color: var(--neutral-500);
}

.agent-card__desc {
  font-size: 12px;
  color: var(--neutral-600);
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.agent-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--neutral-100);
  color: var(--neutral-600);
  border-radius: 4px;
}

.agent-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--neutral-100);
}

.ref-count {
  font-size: 11px;
  color: var(--neutral-400);
}

.btn-delete {
  padding: 4px 10px;
  border: 1px solid var(--neutral-200);
  border-radius: 5px;
  background: var(--neutral-0);
  font-size: 11px;
  color: var(--neutral-500);
  cursor: pointer;
}

.btn-delete:hover {
  border-color: #fca5a5;
  color: #dc2626;
  background: #fef2f2;
}

.agent-manage__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--neutral-400);
  font-size: 13px;
}
</style>
