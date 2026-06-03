<template>
  <div class="step-draft">
    <h2 class="step-draft__title">编辑技能草稿</h2>

    <div class="step-draft__section">
      <div class="step-draft__section-header">
        <h3>基本信息</h3>
      </div>
      <div class="step-draft__form">
        <label>名称 <input v-model="draft.name" /></label>
        <label>描述 <input v-model="draft.description" /></label>
      </div>
    </div>

    <div class="step-draft__section">
      <div class="step-draft__section-header">
        <h3>输入参数 (JSON Schema)</h3>
        <button class="step-draft__regen" @click="regen('input_schema')">AI 重新生成</button>
      </div>
      <textarea class="step-draft__code" v-model="inputSchemaStr" rows="6"></textarea>
    </div>

    <div class="step-draft__section">
      <div class="step-draft__section-header">
        <h3>输出结构 (JSON Schema)</h3>
        <button class="step-draft__regen" @click="regen('output_schema')">AI 重新生成</button>
      </div>
      <textarea class="step-draft__code" v-model="outputSchemaStr" rows="6"></textarea>
    </div>

    <div class="step-draft__section">
      <div class="step-draft__section-header">
        <h3>Prompt 模板</h3>
        <button class="step-draft__regen" @click="regen('prompt_template')">AI 重新生成</button>
      </div>
      <textarea class="step-draft__code" v-model="draft.prompt_template" rows="8"></textarea>
    </div>

    <div class="step-draft__section">
      <div class="step-draft__section-header">
        <h3>工具列表</h3>
        <button class="step-draft__regen" @click="regen('tools')">AI 重新生成</button>
      </div>
      <div v-for="(tool, i) in draft.tools || []" :key="i" class="step-draft__tool">
        <div class="step-draft__tool-header">
          <input v-model="tool.name" placeholder="函数名" class="step-draft__tool-name" />
          <input v-model="tool.description" placeholder="描述" class="step-draft__tool-desc" />
        </div>
        <textarea class="step-draft__code step-draft__tool-code" v-model="tool.code" rows="10"></textarea>
        <p v-if="tool._warnings?.length" class="step-draft__warning">安全警告: {{ tool._warnings.join('; ') }}</p>
      </div>
    </div>

    <div class="step-draft__section">
      <div class="step-draft__section-header">
        <h3>测试用例</h3>
        <button class="step-draft__regen" @click="regen('test_cases')">AI 重新生成</button>
      </div>
      <textarea class="step-draft__code" v-model="testCasesStr" rows="6"></textarea>
    </div>

    <button class="step-draft__btn" @click="handleNext">保存并进入测试</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { updateDraft, regenerateSection, type SkillDef } from '../../../api/skillGen'

const props = defineProps<{ sessionId: string; initialDraft: SkillDef }>()
const emit = defineEmits<{ (e: 'next', draft: SkillDef): void }>()

const draft = ref<SkillDef>({ ...props.initialDraft })

const inputSchemaStr = computed({
  get: () => JSON.stringify(draft.value.input_schema || {}, null, 2),
  set: (v) => { try { draft.value.input_schema = JSON.parse(v) } catch {} }
})

const outputSchemaStr = computed({
  get: () => JSON.stringify(draft.value.output_schema || {}, null, 2),
  set: (v) => { try { draft.value.output_schema = JSON.parse(v) } catch {} }
})

const testCasesStr = computed({
  get: () => JSON.stringify(draft.value.test_cases || [], null, 2),
  set: (v) => { try { draft.value.test_cases = JSON.parse(v) } catch {} }
})

async function regen(section: string) {
  try {
    const resp = await regenerateSection(props.sessionId, section, draft.value)
    const result = (resp as any).data?.result
    if (result !== undefined) {
      (draft.value as any)[section] = result
    }
  } catch { alert('重新生成失败') }
}

async function handleNext() {
  await updateDraft(props.sessionId, draft.value)
  emit('next', draft.value)
}
</script>

<style scoped>
.step-draft__title { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
.step-draft__section { margin-bottom: 24px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
.step-draft__section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.step-draft__section-header h3 { font-size: 14px; font-weight: 600; }
.step-draft__regen { font-size: 11px; padding: 4px 10px; border: 1px solid #4a6fa5; color: #4a6fa5; background: #fff; border-radius: 4px; cursor: pointer; }
.step-draft__regen:hover { background: #f0f6ff; }
.step-draft__form { display: flex; flex-direction: column; gap: 10px; }
.step-draft__form label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #666; }
.step-draft__form input { padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 14px; }
.step-draft__code { width: 100%; padding: 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-family: 'Menlo', 'Monaco', monospace; font-size: 12px; resize: vertical; }
.step-draft__tool { margin-bottom: 16px; padding: 12px; background: #f8f9fa; border-radius: 6px; }
.step-draft__tool-header { display: flex; gap: 8px; margin-bottom: 8px; }
.step-draft__tool-name { width: 200px; padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; font-family: monospace; }
.step-draft__tool-desc { flex: 1; padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; }
.step-draft__tool-code { background: #1e1e1e; color: #d4d4d4; border: none; }
.step-draft__warning { font-size: 11px; color: #d32f2f; margin-top: 4px; }
.step-draft__btn { padding: 10px 24px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-draft__btn:hover { background: #3d5f8c; }
</style>
