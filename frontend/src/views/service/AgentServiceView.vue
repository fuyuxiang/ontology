<template>
  <div class="aw agent-list">
    <header class="aw-header">
      <div>
        <h1>智能体应用</h1>
        <p class="aw-muted">围绕业务任务配置本体、技能与执行范围。</p>
      </div>
      <button v-if="canEdit" class="aw-button aw-primary" @click="router.push('/agent/manage/new')">
        + 新建智能体
      </button>
    </header>
    <div v-if="error" class="aw-alert aw-error" role="alert">
      {{ error }}<button class="aw-link" @click="loadAgents">重试</button>
    </div>
    <div class="agent-list-toolbar">
      <input
        v-model="searchText"
        aria-label="搜索智能体"
        placeholder="搜索名称或业务目标…"
      /><select v-model="statusFilter" aria-label="按状态筛选">
        <option value="all">全部状态</option>
        <option value="draft">草稿</option>
        <option value="published">已发布</option>
      </select>
    </div>
    <p v-if="loading" class="aw-empty">正在加载智能体…</p>
    <div v-else-if="filteredAgents.length" class="agent-list-cards">
      <article v-for="agent in filteredAgents" :key="agent.id" class="aw-card agent-list-card">
        <div class="aw-row aw-between">
          <h2>{{ agent.name }}</h2>
          <span class="aw-pill" :class="agent.status === 'published' ? 'aw-green' : 'aw-amber'">{{
            agent.status === 'published' ? '已发布' : '草稿'
          }}</span>
        </div>
        <p class="aw-muted">{{ agent.description || '尚未填写业务目标' }}</p>
        <div class="aw-row">
          <span v-if="agent.current_version" class="aw-pill aw-blue"
            >v{{ agent.current_version }}</span
          ><span class="aw-pill"
            >{{
              (agent.skill_bindings || agent.tools_config?.skill_bindings || []).length
            }}
            项技能</span
          ><span v-for="tag in agent.tags || []" :key="tag" class="aw-pill">{{ tag }}</span
          ><span v-if="agent.has_changes" class="aw-pill aw-amber">草稿有修改</span>
        </div>
        <footer class="aw-row aw-between">
          <small
            class="aw-muted"
            :title="(agent.referenced_scenes || []).map((s) => s.name).join('、')"
            >被 {{ agent.referenced_scenes?.length || 0 }} 个场景引用</small
          >
          <div class="aw-row">
            <button
              class="aw-link aw-danger"
              :disabled="deleting === agent.id || !canEdit"
              @click="removeAgent(agent)"
            >
              {{ deleting === agent.id ? '删除中…' : '删除' }}</button
            ><button class="aw-link" @click="router.push(`/agent/manage/${agent.id}`)">
              配置与调试 →
            </button>
          </div>
        </footer>
      </article>
    </div>
    <p v-else class="aw-empty">
      {{ agents.length ? '没有匹配的智能体。' : '暂无智能体，创建应用并配置本体与业务技能。' }}
    </p>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { agentsApi, type AgentItem } from '../../api/agents'
import { skillError } from '../../api/skills'
import { useAuthStore } from '../../store/auth'
const router = useRouter()
const authStore = useAuthStore()
const canEdit = computed(() => ['admin', 'editor'].includes(authStore.user?.role || ''))
const searchText = ref('')
const statusFilter = ref('all')
const agents = ref<AgentItem[]>([])
const loading = ref(false)
const error = ref('')
const deleting = ref('')
const filteredAgents = computed(() =>
  agents.value.filter(
    (a) =>
      (statusFilter.value === 'all' || a.status === statusFilter.value) &&
      (!searchText.value.trim() ||
        `${a.name} ${a.description}`.toLowerCase().includes(searchText.value.trim().toLowerCase())),
  ),
)
async function loadAgents() {
  loading.value = true
  error.value = ''
  try {
    if (!authStore.user) await authStore.fetchUser()
    agents.value = await agentsApi.list()
  } catch (e) {
    error.value = skillError(e)
  } finally {
    loading.value = false
  }
}
async function removeAgent(agent: AgentItem) {
  if (!canEdit.value) return
  if (agent.referenced_scenes?.length) {
    error.value = `「${agent.name}」被 ${agent.referenced_scenes.length} 个场景引用，请先解除引用后删除。`
    return
  }
  if (!window.confirm(`删除智能体「${agent.name}」及相关配置？`)) return
  deleting.value = agent.id
  error.value = ''
  try {
    await agentsApi.delete(agent.id)
    agents.value = agents.value.filter((a) => a.id !== agent.id)
  } catch (e) {
    error.value = skillError(e)
  } finally {
    deleting.value = ''
  }
}
onMounted(loadAgents)
</script>
<style src="../../styles/agent-workbench.css"></style>
<style scoped>
.agent-list {
  padding-bottom: 20px;
}
.agent-list-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px;
  gap: 12px;
  margin: 0 22px 18px;
}
.agent-list-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 0 22px;
}
.agent-list-card {
  margin: 0;
  display: flex;
  flex-direction: column;
  min-height: 215px;
}
.agent-list-card h2 {
  margin: 0;
  font-size: 15px;
}
.agent-list-card > p {
  flex: 1;
  min-height: 45px;
}
.agent-list-card footer {
  border-top: 1px solid var(--neutral-200);
  padding-top: 12px;
  margin-top: 16px;
  font-size: 12px;
}
@media (max-width: 1150px) {
  .agent-list-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 700px) {
  .agent-list-cards {
    grid-template-columns: minmax(0, 1fr);
    margin: 0 16px;
  }
  .agent-list-toolbar {
    grid-template-columns: minmax(0, 1fr);
    margin: 0 16px 16px;
  }
  .agent-list-toolbar select {
    width: 100%;
  }
}
</style>
