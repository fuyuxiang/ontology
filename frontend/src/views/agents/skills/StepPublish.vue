<template>
  <div class="step-publish">
    <h2 class="step-publish__title">发布技能</h2>

    <div class="step-publish__summary">
      <div class="step-publish__item"><span>技能名称</span><strong>{{ props.draft.name }}</strong></div>
      <div class="step-publish__item"><span>描述</span><span>{{ props.draft.description }}</span></div>
      <div class="step-publish__item"><span>工具数量</span><span>{{ props.draft.tools?.length || 0 }} 个</span></div>
      <div class="step-publish__item"><span>测试用例</span><span>{{ props.draft.test_cases?.length || 0 }} 个</span></div>
    </div>

    <div class="step-publish__field">
      <label>变更说明</label>
      <textarea v-model="changeLog" rows="3" placeholder="描述本次发布的内容..."></textarea>
    </div>

    <button class="step-publish__btn" :disabled="publishing" @click="handlePublish">
      {{ publishing ? '发布中...' : '确认发布' }}
    </button>

    <div v-if="published" class="step-publish__success">
      <p>发布成功! 版本号: v{{ publishedVersion }}</p>
      <button class="step-publish__go" @click="$router.push(`/agent/toolbox/${publishedId}`)">查看技能详情</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { publishSkill, type SkillDef } from '../../../api/skillGen'

const props = defineProps<{ sessionId: string; draft: SkillDef }>()

const changeLog = ref('')
const publishing = ref(false)
const published = ref(false)
const publishedId = ref('')
const publishedVersion = ref(0)

async function handlePublish() {
  publishing.value = true
  try {
    const resp = await publishSkill(props.sessionId, changeLog.value, '')
    publishedId.value = (resp as any).data?.skill_id || ''
    publishedVersion.value = (resp as any).data?.version || 1
    published.value = true
  } catch { alert('发布失败，请重试') }
  finally { publishing.value = false }
}
</script>

<style scoped>
.step-publish__title { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
.step-publish__summary { border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.step-publish__item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.step-publish__item:last-child { border-bottom: none; }
.step-publish__item span:first-child { color: #666; }
.step-publish__item strong { font-weight: 600; color: #1a1a2e; }
.step-publish__field { margin-bottom: 20px; }
.step-publish__field label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
.step-publish__field textarea { width: 100%; padding: 10px 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 13px; resize: vertical; }
.step-publish__btn { padding: 10px 24px; background: #1a8a3a; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-publish__btn:disabled { opacity: 0.5; }
.step-publish__btn:hover:not(:disabled) { background: #147a30; }
.step-publish__success { margin-top: 20px; padding: 16px; background: #e6f7e9; border-radius: 8px; text-align: center; }
.step-publish__success p { font-size: 14px; color: #1a8a3a; font-weight: 600; margin-bottom: 12px; }
.step-publish__go { padding: 8px 16px; background: #fff; border: 1px solid #1a8a3a; color: #1a8a3a; border-radius: 6px; font-size: 13px; cursor: pointer; }
</style>
