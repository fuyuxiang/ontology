<template>
  <div class="skill-list">
    <div class="skill-list__header">
      <h1 class="skill-list__title">技能管理</h1>
      <button class="skill-list__create-btn" @click="$router.push('/agent/toolbox/create')">创建技能</button>
    </div>
    <p class="skill-list__desc">管理可供智能体调用的技能，支持基于本体资产通过AI自动生成</p>

    <div class="skill-list__grid" v-if="skills.length">
      <div class="skill-card" v-for="s in skills" :key="s.id" @click="$router.push(`/agent/toolbox/${s.id}`)">
        <div class="skill-card__top">
          <span class="skill-card__name">{{ s.name }}</span>
          <span class="skill-card__badge" :class="'skill-card__badge--' + s.status">{{ statusLabel(s.status) }}</span>
        </div>
        <p class="skill-card__desc">{{ s.description || '暂无描述' }}</p>
        <div class="skill-card__meta">
          <span>v{{ s.current_version || 0 }}</span>
          <span>{{ s.skill_type === 'generated' ? 'AI生成' : '内置' }}</span>
          <span v-if="s.created_by">{{ s.created_by }}</span>
        </div>
      </div>
    </div>

    <div class="skill-list__empty" v-else-if="!loading">
      <p>暂无技能，点击上方按钮创建第一个</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { skillsApi, type SkillItem } from '../../../api/skills'

const skills = ref<SkillItem[]>([])
const loading = ref(true)

function statusLabel(status: string) {
  const map: Record<string, string> = { active: '生效', draft: '草稿', deprecated: '已废弃' }
  return map[status] || status
}

onMounted(async () => {
  try {
    skills.value = await skillsApi.list()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.skill-list { max-width: 1200px; margin: 0 auto; padding: 32px 24px; }
.skill-list__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.skill-list__title { font-size: 22px; font-weight: 600; color: #1a1a2e; }
.skill-list__create-btn { padding: 8px 20px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.skill-list__create-btn:hover { background: #3d5f8c; }
.skill-list__desc { font-size: 13px; color: #666; margin-bottom: 24px; }
.skill-list__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.skill-card { padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px; cursor: pointer; transition: box-shadow 0.2s; }
.skill-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.skill-card__top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.skill-card__name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.skill-card__badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.skill-card__badge--active { background: #e6f7e9; color: #1a8a3a; }
.skill-card__badge--draft { background: #fff3e0; color: #e65100; }
.skill-card__badge--deprecated { background: #f0f0f0; color: #999; }
.skill-card__desc { font-size: 13px; color: #555; margin-bottom: 12px; line-height: 1.5; }
.skill-card__meta { display: flex; gap: 12px; font-size: 11px; color: #999; }
.skill-list__empty { text-align: center; padding: 60px 0; color: #999; }
</style>
