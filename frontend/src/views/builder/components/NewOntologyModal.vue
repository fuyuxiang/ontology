<template>
  <div class="ob-new-modal-mask" @click.self="emit('update:open', false)">
    <div class="ob-new-modal" @click.stop>
      <div class="ob-new-modal-head">
        <h2>新建本体</h2>
        <button type="button" class="ob-new-close" aria-label="关闭新建本体弹窗" @click="emit('update:open', false)">×</button>
      </div>

      <div class="ob-new-steps">
        <template v-for="(s, idx) in stepDefs" :key="s.num">
          <div :class="['ob-new-step', { active: step === s.num, done: step > s.num }]">
            <span class="ob-new-step-num">{{ s.num }}</span>
            <span>{{ s.label }}</span>
          </div>
          <div v-if="idx < stepDefs.length - 1" :class="['ob-new-step-line', { done: step > s.num }]"></div>
        </template>
      </div>

      <div v-if="step === 1" class="ob-new-panel">
        <label class="ob-new-label" for="new-scene-name">任务名称 <span>*</span></label>
        <input
          id="new-scene-name"
          :class="['ob-new-input', { 'ob-new-input-error': !!nameError }]"
          v-model="form.ontologyName"
          placeholder="例如：退单根因分析"
          autofocus
        />
        <div v-if="nameError" class="ob-new-field-error">{{ nameError }}</div>

        <div class="ob-quick-box">
          <div class="ob-quick-title">快速填入</div>
          <div class="ob-quick-list">
            <button
              v-for="p in QUICK_TITLES"
              :key="p"
              type="button"
              class="ob-quick-pill"
              @click="form.ontologyName = p"
            >{{ p }}</button>
          </div>
        </div>
      </div>

      <div v-if="step === 2" class="ob-new-panel">
        <div class="ob-scene-list">
          <button
            v-for="s in SCENARIO_PRESETS"
            :key="s.id"
            type="button"
            :class="['ob-scene-option', `ob-scene-${s.tone}`, { selected: form.scenarioId === s.id }]"
            @click="selectScene(s)"
          >
            <span class="ob-scene-icon">{{ s.short }}</span>
            <span class="ob-scene-main">
              <strong>{{ s.title }}</strong>
              <span>{{ s.description }}</span>
            </span>
            <span class="ob-scene-meta">{{ s.meta }}</span>
            <span class="ob-scene-radio"></span>
          </button>

          <div :class="['ob-scene-custom-box', { open: customOpen }]">
            <button type="button" class="ob-scene-custom-trigger" @click="customOpen = !customOpen">
              <span class="ob-scene-icon">{{ customOpen ? '×' : '+' }}</span>
              <span class="ob-scene-main">
                <strong>新建场景</strong>
                <span>自定义业务场景，后续可在 AI 构建中补充知识线索</span>
              </span>
            </button>
            <div v-if="customOpen" class="ob-custom-scene-form">
              <label class="ob-new-label" for="custom-scene-name">场景名称</label>
              <div class="ob-custom-scene-row">
                <input
                  id="custom-scene-name"
                  class="ob-new-input"
                  v-model="customSceneName"
                  placeholder="例如：宽带故障挽留"
                />
                <button type="button" class="ob-custom-scene-add" @click="confirmCustom">确认</button>
                <button type="button" class="ob-custom-scene-cancel" @click="cancelCustom">取消</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="step === 3" class="ob-new-panel">
        <div class="ob-method-grid">
          <div
            role="button"
            tabindex="0"
            :class="['ob-method-card', 'ob-method-ai', { selected: form.buildMethod === 'ai' }]"
            @click="form.buildMethod = 'ai'"
            @keydown="onMethodKey($event, 'ai')"
          >
            <span class="ob-method-icon">AI</span>
            <strong>AI 构建新本体</strong>
            <span>从业务场景对话出发，Copilot 智能匹配资产，自动识别主体、属性、关系，全程 AI 辅助</span>
            <em>适合业务分析师</em>
          </div>
          <div
            role="button"
            tabindex="0"
            :class="['ob-method-card', 'ob-method-upload', { selected: form.buildMethod === 'upload' }]"
            @click="form.buildMethod = 'upload'"
            @keydown="onMethodKey($event, 'upload')"
          >
            <span class="ob-method-icon">UP</span>
            <strong>上传本体文件构建</strong>
            <span>上传已构建好的 OWL / JSON 本体文件，系统解析对象、属性与关系后进入导入审核流程</span>
            <em>适合本体工程师</em>
            <div v-if="form.buildMethod === 'upload'" class="ob-method-note">开始构建后进入本体导入步骤，在下一步选择 OWL / JSON 文件。</div>
          </div>
        </div>
      </div>

      <div class="ob-new-footer">
        <button v-if="step === 1" type="button" class="ob-new-secondary" @click="emit('update:open', false)">取消</button>
        <button v-else type="button" class="ob-new-secondary" @click="step--">上一步</button>

        <button
          v-if="step < 3"
          type="button"
          class="ob-new-primary"
          :disabled="!canNext"
          @click="next"
        >下一步</button>
        <button v-else type="button" class="ob-new-primary" @click="submit">开始构建</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { BuildMethod, ScenarioCard } from '../../../types/builder'

const props = defineProps<{ open: boolean; defaultMethod?: BuildMethod }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'submit', payload: { ontologyName: string; scenarioId: string; scenarioName: string; buildMethod: BuildMethod }): void
}>()

const QUICK_TITLES = ['退单根因分析', '政企智能问数', 'FTTR续约策略策划']
const stepDefs = [
  { num: 1, label: '命名' },
  { num: 2, label: '选择场景' },
  { num: 3, label: '构建方式' },
] as const

const SCENARIO_PRESETS: ScenarioCard[] = [
  { id: 'refund-root-cause', short: '归因', title: '退单根因分析', description: '基于退单行为本体，自动归因退单原因，输出可执行的服务改善与挽留策略', meta: '退单 · 归因 · 挽留', tone: 'slate' },
  { id: 'enterprise-qa',     short: '问数', title: '政企智能问数', description: '面向政企客户的自然语言问数场景，通过本体语义层驱动 Text-to-SQL 精准查询', meta: '政企 · NL2SQL · 问答', tone: 'purple' },
  { id: 'fttr-renewal',      short: '续约', title: 'FTTR续约策略策划', description: '合约到期用户续约保有，按ARPU分档推送个性化续约方案，降低用户流失率', meta: '宽带 · 续约 · 营销', tone: 'blue' },
]

const step = ref(1)
const form = reactive<{ ontologyName: string; scenarioId: string; scenarioName: string; buildMethod: BuildMethod }>({
  ontologyName: '', scenarioId: '', scenarioName: '', buildMethod: 'ai',
})
const nameError = ref('')
const customOpen = ref(false)
const customSceneName = ref('')

watch(() => props.open, (v) => {
  if (!v) return
  step.value = 1
  form.ontologyName = ''
  form.scenarioId = ''
  form.scenarioName = ''
  form.buildMethod = props.defaultMethod || 'ai'
  nameError.value = ''
  customOpen.value = false
  customSceneName.value = ''
})

function selectScene(s: ScenarioCard) {
  form.scenarioId = s.id
  form.scenarioName = s.title
  customOpen.value = false
  customSceneName.value = ''
}

function confirmCustom() {
  const v = customSceneName.value.trim()
  if (!v) return
  form.scenarioId = `custom-${Date.now().toString(36)}`
  form.scenarioName = v
  customOpen.value = false
}

function cancelCustom() {
  customOpen.value = false
  customSceneName.value = ''
}

const canNext = computed(() => {
  if (step.value === 1) return !!form.ontologyName.trim() && !nameError.value
  if (step.value === 2) return !!form.scenarioId
  return !!form.buildMethod
})

watch(() => form.ontologyName, (v) => {
  nameError.value = !v.trim() ? '' : ''
})

function next() {
  if (!canNext.value) return
  if (step.value === 1) {
    if (!form.ontologyName.trim()) { nameError.value = '任务名称不能为空'; return }
    step.value = 2
    return
  }
  step.value++
}

function onMethodKey(e: KeyboardEvent, m: BuildMethod) {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); form.buildMethod = m }
}

function submit() {
  emit('submit', { ...form })
}
</script>
