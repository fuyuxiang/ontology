<template>
  <div class="step-test">
    <h2 class="step-test__title">测试验证</h2>

    <div class="step-test__layout">
      <div class="step-test__left">
        <h3>输入参数</h3>
        <div v-for="(prop, key) in inputProps" :key="key" class="step-test__field">
          <label>{{ key }}</label>
          <input v-model="testInput[key as string]" :placeholder="prop.description || key" />
        </div>
        <button class="step-test__run-btn" :disabled="running" @click="runTest">
          {{ running ? '执行中...' : '执行测试' }}
        </button>
      </div>

      <div class="step-test__right">
        <h3>执行结果</h3>
        <div v-if="results.length" class="step-test__results">
          <div v-for="(r, i) in results" :key="i" class="step-test__result" :class="r.success ? 'step-test__result--pass' : 'step-test__result--fail'">
            <span class="step-test__result-badge">{{ r.success ? 'PASS' : 'FAIL' }}</span>
            <span class="step-test__result-name">{{ r.tool }}</span>
            <pre class="step-test__result-output">{{ r.success ? JSON.stringify(r.output, null, 2) : r.error }}</pre>
          </div>
        </div>
        <p v-else class="step-test__placeholder">点击"执行测试"查看结果</p>
      </div>
    </div>

    <div class="step-test__cases" v-if="props.draft.test_cases?.length">
      <h3>预设测试用例</h3>
      <div v-for="(tc, i) in props.draft.test_cases" :key="i" class="step-test__case">
        <span class="step-test__case-label">用例 {{ i + 1 }}</span>
        <code>{{ JSON.stringify(tc.input) }}</code>
      </div>
      <button class="step-test__batch-btn" :disabled="running" @click="runBatch">批量执行</button>
    </div>

    <button class="step-test__btn" :disabled="!allPassed" @click="emit('next')">
      {{ allPassed ? '下一步' : '请确保测试通过' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { testSkill, type SkillDef } from '../../../api/skillGen'

const props = defineProps<{ draft: SkillDef }>()
const emit = defineEmits<{ (e: 'next'): void }>()

const testInput = ref<Record<string, any>>({})
const results = ref<any[]>([])
const running = ref(false)

const inputProps = computed(() => props.draft.input_schema?.properties || {})
const allPassed = computed(() => results.value.length > 0 && results.value.every(r => r.success))

async function runTest() {
  running.value = true
  results.value = []
  try {
    const resp = await testSkill(props.draft, testInput.value)
    results.value = (resp as any).data?.results || []
  } catch { alert('测试执行失败') }
  finally { running.value = false }
}

async function runBatch() {
  running.value = true
  results.value = []
  try {
    for (const tc of props.draft.test_cases || []) {
      const resp = await testSkill(props.draft, tc.input)
      results.value.push(...((resp as any).data?.results || []))
    }
  } catch { alert('批量测试失败') }
  finally { running.value = false }
}
</script>

<style scoped>
.step-test__title { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
.step-test__layout { display: flex; gap: 20px; margin-bottom: 24px; }
.step-test__left { flex: 1; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
.step-test__left h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.step-test__field { margin-bottom: 10px; }
.step-test__field label { display: block; font-size: 12px; color: #666; margin-bottom: 4px; }
.step-test__field input { width: 100%; padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 13px; }
.step-test__run-btn { margin-top: 12px; padding: 8px 20px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.step-test__run-btn:disabled { opacity: 0.5; }
.step-test__right { flex: 1; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
.step-test__right h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.step-test__results { max-height: 300px; overflow-y: auto; }
.step-test__result { margin-bottom: 12px; padding: 10px; border-radius: 6px; }
.step-test__result--pass { background: #e6f7e9; }
.step-test__result--fail { background: #ffeaea; }
.step-test__result-badge { font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 3px; margin-right: 8px; }
.step-test__result--pass .step-test__result-badge { background: #1a8a3a; color: #fff; }
.step-test__result--fail .step-test__result-badge { background: #d32f2f; color: #fff; }
.step-test__result-name { font-size: 13px; font-weight: 500; }
.step-test__result-output { font-size: 11px; margin-top: 6px; white-space: pre-wrap; max-height: 100px; overflow-y: auto; }
.step-test__placeholder { text-align: center; color: #999; font-size: 13px; padding: 40px; }
.step-test__cases { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 20px; }
.step-test__cases h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.step-test__case { padding: 6px 10px; background: #f8f9fa; border-radius: 4px; margin-bottom: 6px; font-size: 12px; }
.step-test__case-label { font-weight: 600; margin-right: 8px; }
.step-test__batch-btn { margin-top: 8px; padding: 6px 16px; background: #fff; border: 1px solid #4a6fa5; color: #4a6fa5; border-radius: 6px; font-size: 12px; cursor: pointer; }
.step-test__btn { padding: 10px 24px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-test__btn:disabled { opacity: 0.5; cursor: default; }
</style>
