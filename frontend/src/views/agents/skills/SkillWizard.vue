<template>
  <div class="skill-wizard">
    <div class="skill-wizard__steps">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="skill-wizard__step"
        :class="{ 'skill-wizard__step--active': current === i, 'skill-wizard__step--done': current > i }"
      >
        <span class="skill-wizard__step-num">{{ i + 1 }}</span>
        <span class="skill-wizard__step-label">{{ step }}</span>
      </div>
    </div>

    <div class="skill-wizard__body">
      <StepAssets v-if="current === 0" @next="onAssetsNext" />
      <StepChat v-else-if="current === 1" :session-id="sessionId" :assets-context="assetsContext" @next="onChatNext" />
      <StepDraft v-else-if="current === 2" :session-id="sessionId" :initial-draft="draft" @next="onDraftNext" />
      <StepTest v-else-if="current === 3" :draft="draft" @next="onTestNext" />
      <StepPublish v-else-if="current === 4" :session-id="sessionId" :draft="draft" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import StepAssets from './StepAssets.vue'
import StepChat from './StepChat.vue'
import StepDraft from './StepDraft.vue'
import StepTest from './StepTest.vue'
import StepPublish from './StepPublish.vue'
import type { SkillDef } from '../../../api/skillGen'

const steps = ['选择资产', 'AI对话', '编辑草稿', '测试验证', '发布']
const current = ref(0)
const sessionId = ref('')
const assetsContext = ref('')
const draft = ref<SkillDef>({})

function onAssetsNext(payload: { sessionId: string; assetsContext: string }) {
  sessionId.value = payload.sessionId
  assetsContext.value = payload.assetsContext
  current.value = 1
}

function onChatNext(skillDef: SkillDef) {
  draft.value = skillDef
  current.value = 2
}

function onDraftNext(updatedDraft: SkillDef) {
  draft.value = updatedDraft
  current.value = 3
}

function onTestNext() {
  current.value = 4
}
</script>

<style scoped>
.skill-wizard { max-width: 1000px; margin: 0 auto; padding: 24px; }
.skill-wizard__steps { display: flex; gap: 4px; margin-bottom: 32px; padding: 16px; background: #f8f9fa; border-radius: 10px; }
.skill-wizard__step { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 6px; font-size: 13px; color: #999; flex: 1; }
.skill-wizard__step--active { background: #4a6fa5; color: #fff; }
.skill-wizard__step--done { color: #1a8a3a; }
.skill-wizard__step-num { width: 22px; height: 22px; border-radius: 50%; background: #e0e0e0; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; }
.skill-wizard__step--active .skill-wizard__step-num { background: rgba(255,255,255,0.3); color: #fff; }
.skill-wizard__step--done .skill-wizard__step-num { background: #e6f7e9; color: #1a8a3a; }
.skill-wizard__body { min-height: 400px; }
</style>
