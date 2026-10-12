<template>
  <div class="skills-page">
    <header class="skills-header">
      <div>
        <div class="eyebrow">本体应用 · 能力资产</div>
        <h1>业务技能</h1>
        <p>沉淀专家的操作方法，供智能体按任务使用。每次发布保留独立版本。</p>
      </div>
      <a-button v-if="canCreate" type="primary" @click="router.push('/skills/new')"
        >＋ 新建技能</a-button
      >
    </header>
    <div class="skills-stats">
      <div>
        <span>技能总数</span><strong>{{ skills.length }}</strong>
      </div>
      <div>
        <span>已发布</span><strong>{{ skills.filter((s) => s.status === 'active').length }}</strong>
      </div>
      <div>
        <span>待完善草稿</span
        ><strong>{{ skills.filter((s) => s.status === 'draft' || s.has_changes).length }}</strong>
      </div>
    </div>
    <section class="skills-panel">
      <div class="skills-filters">
        <a-input
          v-model:value="search"
          placeholder="搜索技能名称、用途或标签"
          allow-clear
          class="skills-search"
          aria-label="搜索技能"
        />
        <a-select
          v-model:value="ontology"
          :options="ontologyOptions"
          style="min-width: 180px"
          aria-label="筛选关联本体"
        />
        <a-select
          v-model:value="status"
          :options="statusOptions"
          style="min-width: 140px"
          aria-label="筛选技能状态"
        />
        <span class="filter-count">{{ filtered.length }} 项</span>
        <a-button @click="load" :loading="loading">刷新</a-button>
      </div>
      <a-alert v-if="error" :message="error" type="error" show-icon class="load-error"
        ><template #action><a-button size="small" @click="load">重试</a-button></template></a-alert
      >
      <a-table
        :columns="columns"
        :data-source="filtered"
        :loading="loading"
        row-key="id"
        :pagination="{ pageSize: 10, showSizeChanger: true }"
        :scroll="{ x: 940 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'"
            ><RouterLink :to="`/skills/${record.id}`" class="skill-name">{{
              record.name
            }}</RouterLink>
            <p class="skill-description">{{ record.description || '尚未填写技能用途' }}</p>
            <div class="skill-tags">
              <a-tag v-for="tag in record.tags" :key="tag">{{ tag }}</a-tag>
            </div></template
          >
          <template v-else-if="column.key === 'ontology'">{{
            ontologyName(record.ontology_id)
          }}</template>
          <template v-else-if="column.key === 'version'"
            ><span>{{ record.current_version ? `v${record.current_version}` : '未发布' }}</span>
            <div v-if="record.has_changes && record.current_version" class="draft-note">
              有待发布修改
            </div></template
          >
          <template v-else-if="column.key === 'references'"
            >{{ record.ref_count || 0 }} 个智能体</template
          >
          <template v-else-if="column.key === 'status'"
            ><a-tag
              :color="
                record.status === 'active'
                  ? 'green'
                  : record.status === 'archived'
                    ? 'default'
                    : 'blue'
              "
              >{{ statusLabel(record.status) }}</a-tag
            ></template
          >
          <template v-else-if="column.key === 'action'"
            ><a-space
              ><a-button type="link" size="small" @click="router.push(`/skills/${record.id}`)">{{
                record.can_edit === false ? '查看' : '编辑'
              }}</a-button
              ><a-dropdown v-if="record.can_edit !== false"
                ><a-button type="text" size="small">更多 ▾</a-button
                ><template #overlay
                  ><a-menu @click="({ key }: { key: string }) => operate(record, key)"
                    ><a-menu-item v-if="record.status === 'archived'" key="restore"
                      >恢复技能</a-menu-item
                    ><a-menu-item v-else key="archive">归档技能</a-menu-item
                    ><a-menu-item key="delete" danger :disabled="!!record.ref_count"
                      >删除技能{{ record.ref_count ? '（正在被引用）' : '' }}</a-menu-item
                    ></a-menu
                  ></template
                ></a-dropdown
              ></a-space
            ></template
          >
        </template>
        <template #emptyText
          ><a-empty
            :description="
              skills.length
                ? '没有匹配的技能，请调整筛选条件'
                : '暂无业务技能，创建第一个技能沉淀业务经验'
            "
        /></template>
      </a-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import { skillsApi, skillError, type SkillItem } from '../../api/skills'
import { scenarioApi, type Scenario } from '../../api/scenarios'
import { useToast } from '../../composables/useToast'
import { useAuthStore } from '../../store/auth'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const authStore = useAuthStore()
const canCreate = computed(() => authStore.hasPermission('rule:write'))
const skills = ref<SkillItem[]>([])
const ontologies = ref<Scenario[]>([])
const search = ref('')
const ontology = ref(typeof route.query.ontology_id === 'string' ? route.query.ontology_id : 'all')
const status = ref('all')
const loading = ref(true)
const error = ref('')
const statusOptions = [
  { value: 'all', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '已发布' },
  { value: 'archived', label: '已归档' },
]
const ontologyOptions = computed(() => [
  { value: 'all', label: '全部本体' },
  { value: 'none', label: '未关联本体' },
  ...ontologies.value.map((o) => ({ value: o.id, label: o.name })),
])
const filtered = computed(() =>
  skills.value.filter((s) => {
    const q = search.value.trim().toLowerCase()
    return (
      (status.value === 'all' || s.status === status.value) &&
      (ontology.value === 'all' ||
        (ontology.value === 'none' ? !s.ontology_id : s.ontology_id === ontology.value)) &&
      (!q || `${s.name} ${s.description} ${(s.tags || []).join(' ')}`.toLowerCase().includes(q))
    )
  }),
)
const columns = [
  { title: '技能 / 用途', key: 'name', width: 300 },
  { title: '关联本体', key: 'ontology', width: 170 },
  { title: '在线版本', key: 'version', width: 130 },
  { title: '引用', key: 'references', width: 120 },
  { title: '状态', key: 'status', width: 100 },
  { title: '操作', key: 'action', width: 130 },
]
function ontologyName(id: string | null) {
  return ontologies.value.find((o) => o.id === id)?.name || (id ? '本体已不可用' : '通用技能')
}
function statusLabel(value: string) {
  return (
    ({ draft: '草稿', active: '已发布', archived: '已归档' } as Record<string, string>)[value] ||
    value
  )
}
async function load() {
  loading.value = true
  error.value = ''
  const results = await Promise.allSettled([
    skillsApi.list(),
    scenarioApi.list(),
    authStore.user ? Promise.resolve() : authStore.fetchUser(),
  ])
  if (results[0].status === 'fulfilled') skills.value = results[0].value
  else error.value = skillError(results[0].reason, '技能列表加载失败')
  if (results[1].status === 'fulfilled') ontologies.value = results[1].value
  else
    error.value = `${error.value ? `${error.value}；` : ''}本体列表加载失败：${skillError(results[1].reason)}`
  loading.value = false
}
function operate(skill: SkillItem, key: string) {
  const labels: Record<string, string> = { archive: '归档', restore: '恢复', delete: '删除' }
  Modal.confirm({
    title: `${labels[key]}「${skill.name}」？`,
    content:
      key === 'delete'
        ? '删除后无法恢复。正在被智能体引用的技能不能删除。'
        : key === 'archive'
          ? '归档后不再允许新挂载，已有智能体固定使用的版本继续保留。'
          : '恢复后可以继续编辑和发布技能。',
    okText: labels[key],
    cancelText: '取消',
    okButtonProps: { danger: key === 'delete' },
    async onOk() {
      try {
        if (key === 'archive') await skillsApi.archive(skill.id)
        else if (key === 'restore') await skillsApi.restore(skill.id)
        else await skillsApi.delete(skill.id)
        toast.success(`技能已${labels[key]}`)
        await load()
      } catch (e) {
        toast.error(skillError(e))
        throw e
      }
    },
  })
}
onMounted(load)
</script>

<style scoped>
.skills-page {
  max-width: 1480px;
  margin: auto;
}
.skills-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  margin: 4px 0 24px;
}
.eyebrow {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}
h1 {
  font-size: 24px;
  margin: 0 0 8px;
  color: #1e293b;
  font-weight: 650;
}
.skills-header p {
  color: #64748b;
  font-size: 13px;
  margin: 0;
}
.skills-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.skills-stats > div {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.skills-stats span {
  font-size: 13px;
  color: #64748b;
}
.skills-stats strong {
  font-size: 26px;
  color: #334155;
}
.skills-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}
.skills-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px;
}
.skills-search {
  max-width: 340px;
}
.filter-count {
  margin-left: auto;
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}
.load-error {
  margin: 0 18px 14px;
}
.skill-name {
  font-weight: 600;
  color: #2563eb;
}
.skill-description {
  font-size: 12px;
  color: #64748b;
  margin: 6px 0;
  max-width: 360px;
  line-height: 1.6;
}
.skill-tags:empty {
  display: none;
}
.draft-note {
  font-size: 11px;
  color: #b45309;
  margin-top: 5px;
}
@media (max-width: 1000px) {
  .skills-filters {
    flex-wrap: wrap;
  }
  .skills-search {
    max-width: none;
    width: 100%;
  }
  .skills-header {
    align-items: flex-start;
  }
  .skills-stats {
    gap: 8px;
  }
  .skills-stats > div {
    padding: 12px;
  }
}
</style>
