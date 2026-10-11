<template>
  <section class="application-references">
    <header>
      <div>
        <h2>应用引用</h2>
        <p>查看使用此本体的业务技能与智能体，追踪业务能力的实际使用范围。</p>
      </div>
      <a-button :loading="loading" @click="load">刷新</a-button>
    </header>
    <a-alert v-if="error" :message="error" type="error" show-icon class="reference-error"
      ><template #action><a-button size="small" @click="load">重试</a-button></template></a-alert
    >
    <a-spin :spinning="loading"
      ><div class="reference-columns">
        <section>
          <div class="reference-heading">
            <h3>
              业务技能 <span>{{ skills.length }}</span>
            </h3>
            <RouterLink :to="{ path: '/skills', query: { ontology_id: ontologyId } }"
              >技能中心 ›</RouterLink
            >
          </div>
          <div v-for="skill in skills" :key="skill.id" class="reference-row">
            <div>
              <RouterLink :to="`/skills/${skill.id}`">{{ skill.name }}</RouterLink>
              <p>{{ skill.description || '尚未填写用途' }}</p>
              <small
                >{{ skill.current_version ? `在线 v${skill.current_version}` : '未发布' }} ·
                {{ skill.ref_count || 0 }} 个智能体引用</small
              >
            </div>
            <a-tag :color="skill.status === 'active' ? 'green' : 'default'">{{
              { draft: '草稿', active: '已发布', archived: '已归档' }[skill.status]
            }}</a-tag>
          </div>
          <a-empty v-if="!skills.length" description="尚无技能引用此本体" />
        </section>
        <section>
          <div class="reference-heading">
            <h3>
              智能体 <span>{{ agents.length }}</span>
            </h3>
            <RouterLink to="/agent/manage">智能体应用 ›</RouterLink>
          </div>
          <div v-for="agent in agents" :key="agent.id" class="reference-row">
            <div>
              <RouterLink :to="`/agent/manage/${agent.id}`">{{ agent.name }}</RouterLink>
              <p>{{ agent.description || '尚未填写用途' }}</p>
              <small>{{ agent.status === 'published' ? '在线应用' : '配置草稿' }}</small>
            </div>
            <a-tag :color="agent.status === 'published' ? 'green' : 'blue'">{{
              agent.status === 'published' ? '已发布' : '草稿'
            }}</a-tag>
          </div>
          <a-empty v-if="!agents.length" description="尚无智能体引用此本体" />
        </section></div
    ></a-spin>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { skillsApi, skillError, type SkillItem } from '../../api/skills'
import { agentsApi, type AgentItem } from '../../api/agents'
const props = defineProps<{ ontologyId: string }>()
const skills = ref<SkillItem[]>([])
const agents = ref<AgentItem[]>([])
const loading = ref(false)
const error = ref('')
let requestId = 0
async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  const results = await Promise.allSettled([
    skillsApi.list({ ontology_id: props.ontologyId }),
    agentsApi.list(),
  ])
  if (id !== requestId) return
  if (results[0].status === 'fulfilled') skills.value = results[0].value
  else {
    skills.value = []
    error.value = skillError(results[0].reason, '技能引用加载失败')
  }
  if (results[1].status === 'fulfilled')
    agents.value = results[1].value.filter((agent) => {
      const config = agent.tools_config || {}
      return (
        (agent.referenced_ontology_ids || []).includes(props.ontologyId) ||
        agent.ontology_id === props.ontologyId ||
        (agent.kb_ids || []).includes(props.ontologyId) ||
        config.ontology_id === props.ontologyId
      )
    })
  else {
    agents.value = []
    error.value = `${error.value ? `${error.value}；` : ''}${skillError(results[1].reason, '智能体引用加载失败')}`
  }
  loading.value = false
}
watch(() => props.ontologyId, load)
onMounted(load)
</script>

<style scoped>
.application-references header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}
.application-references h2 {
  font-size: 18px;
  color: #334155;
  margin: 0 0 8px;
}
.application-references header p {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}
.reference-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.reference-columns > section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 20px;
}
.reference-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.reference-heading h3 {
  margin: 0;
  font-size: 15px;
  color: #334155;
}
.reference-heading h3 span {
  margin-left: 6px;
  color: #64748b;
  font-size: 12px;
}
.reference-heading > a {
  font-size: 12px;
}
.reference-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 0;
  border-top: 1px solid #f1f5f9;
}
.reference-row > div {
  min-width: 0;
}
.reference-row a {
  font-size: 14px;
  font-weight: 500;
}
.reference-row p {
  font-size: 12px;
  color: #64748b;
  line-height: 1.8;
  margin: 6px 0;
}
.reference-row small {
  font-size: 11px;
  color: #94a3b8;
}
.reference-row > .ant-tag {
  height: fit-content;
}
.reference-error {
  margin-bottom: 16px;
}
@media (max-width: 1100px) {
  .reference-columns {
    grid-template-columns: 1fr;
  }
}
</style>
