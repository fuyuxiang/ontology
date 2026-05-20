<template>
  <a-modal
    :open="open"
    :footer="null"
    :closable="false"
    :width="720"
    :mask-closable="false"
    class="ob-new-modal"
    @cancel="emit('update:open', false)"
  >
    <div class="ob-new-modal__body">
      <div class="ob-new-modal__head">
        <div class="ob-new-modal__title">新建本体</div>
        <button class="ob-new-modal__close" @click="emit('update:open', false)">×</button>
      </div>

      <div class="ob-new-steps">
        <div
          v-for="(s, i) in stepLabels"
          :key="i"
          class="ob-new-step"
          :class="{
            'ob-new-step--active': step === i + 1,
            'ob-new-step--done': step > i + 1,
          }"
        >
          <div class="ob-new-step__circle">{{ i + 1 }}</div>
          <div class="ob-new-step__label">{{ s }}</div>
        </div>
      </div>

      <!-- Step 1 命名 -->
      <div v-if="step === 1" class="ob-new-step-body">
        <div class="ob-form-row">
          <label class="ob-label">任务名称 <span class="req">*</span></label>
          <a-input
            v-model:value="form.ontologyName"
            placeholder="例如：退单根因分析"
            size="large"
          />
          <div v-if="nameError" class="ob-error">{{ nameError }}</div>
        </div>

        <div class="ob-quick-box">
          <div class="ob-quick-title">快速填入</div>
          <div class="ob-quick-list">
            <button
              v-for="p in PRESET_TITLES"
              :key="p"
              class="ob-quick-chip"
              @click="form.ontologyName = p"
            >{{ p }}</button>
          </div>
        </div>
      </div>

      <!-- Step 2 选择场景 -->
      <div v-if="step === 2" class="ob-new-step-body">
        <div class="ob-scene-list">
          <div
            v-for="s in SCENARIO_PRESETS"
            :key="s.id"
            class="ob-scene-option"
            :class="[`ob-scene-option--${s.tone}`, { 'ob-scene-option--active': form.scenarioId === s.id }]"
            @click="selectScene(s)"
          >
            <div class="ob-scene-option__icon">{{ s.short }}</div>
            <div class="ob-scene-option__main">
              <div class="ob-scene-option__title">{{ s.title }}</div>
              <div class="ob-scene-option__desc">{{ s.description }}</div>
              <div class="ob-scene-option__meta">{{ s.meta }}</div>
            </div>
            <div class="ob-scene-option__check">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M5 10l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="ob-scene-custom-box">
          <div class="ob-scene-custom-toggle" @click="customOpen = !customOpen">
            <span>{{ customOpen ? '−' : '+' }}</span>
            新建场景
          </div>
          <div v-if="customOpen" class="ob-scene-custom-form">
            <a-input
              v-model:value="customSceneName"
              placeholder="例如：宽带故障挽留"
              size="middle"
              @change="onCustomSceneChange"
            />
          </div>
        </div>
      </div>

      <!-- Step 3 构建方式 -->
      <div v-if="step === 3" class="ob-new-step-body">
        <div class="ob-method-grid">
          <div
            class="ob-method-card ob-method-card--blue"
            :class="{ 'ob-method-card--selected': form.buildMethod === 'ai' }"
            @click="form.buildMethod = 'ai'"
          >
            <div class="ob-method-card__icon">AI</div>
            <div class="ob-method-card__tag">适合业务分析师</div>
            <div class="ob-method-card__title">AI 构建新本体</div>
            <div class="ob-method-card__desc">从业务场景对话出发，Copilot 智能匹配资产，自动识别主体、属性、关系，全程 AI 辅助</div>
          </div>

          <div
            class="ob-method-card ob-method-card--green"
            :class="{ 'ob-method-card--selected': form.buildMethod === 'upload' }"
            @click="form.buildMethod = 'upload'"
          >
            <div class="ob-method-card__icon">UP</div>
            <div class="ob-method-card__tag">适合数据工程师</div>
            <div class="ob-method-card__title">上传本体文件构建</div>
            <div class="ob-method-card__desc">上传已构建好的 OWL / JSON 本体文件，系统解析对象、属性与关系后进入导入审核流程</div>
          </div>
        </div>
      </div>

      <div class="ob-new-modal__footer">
        <a-button @click="emit('update:open', false)">取消</a-button>
        <div style="flex: 1"></div>
        <a-button v-if="step > 1" @click="step--">上一步</a-button>
        <a-button v-if="step < 3" type="primary" :disabled="!canNext" @click="step++">下一步</a-button>
        <a-button v-else type="primary" :disabled="!form.scenarioId || !form.ontologyName" @click="submit">开始构建</a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { SCENARIO_PRESETS } from '../../../data/builderPresets'
import type { BuildMethod, ScenarioCard } from '../../../types/builder'

const props = defineProps<{ open: boolean; defaultMethod?: BuildMethod }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'submit', payload: {
    ontologyName: string
    scenarioId: string
    scenarioName: string
    buildMethod: BuildMethod
  }): void
}>()

const PRESET_TITLES = ['退单根因分析', '政企智能问数', 'FTTR续约策略策划']
const stepLabels = ['命名', '选择场景', '构建方式']

const step = ref(1)
const form = reactive<{
  ontologyName: string
  scenarioId: string
  scenarioName: string
  buildMethod: BuildMethod
}>({
  ontologyName: '',
  scenarioId: '',
  scenarioName: '',
  buildMethod: 'ai',
})
const nameError = ref('')
const customOpen = ref(false)
const customSceneName = ref('')

watch(() => props.open, (v) => {
  if (v) {
    step.value = 1
    form.ontologyName = ''
    form.scenarioId = ''
    form.scenarioName = ''
    form.buildMethod = props.defaultMethod || 'ai'
    nameError.value = ''
    customOpen.value = false
    customSceneName.value = ''
  }
})

function selectScene(s: ScenarioCard) {
  form.scenarioId = s.id
  form.scenarioName = s.title
  customSceneName.value = ''
}

function onCustomSceneChange() {
  if (customSceneName.value.trim()) {
    form.scenarioId = `custom-${Date.now().toString(36)}`
    form.scenarioName = customSceneName.value.trim()
  }
}

const canNext = ref(true)
watch(() => form.ontologyName, (v) => {
  nameError.value = !v.trim() ? '任务名称不能为空' : ''
})
watch([() => form.ontologyName, () => form.scenarioId, step], () => {
  if (step.value === 1) canNext.value = !!form.ontologyName.trim()
  else if (step.value === 2) canNext.value = !!form.scenarioId
  else canNext.value = !!form.buildMethod
}, { immediate: true })

function submit() {
  emit('submit', { ...form })
}
</script>

<style scoped>
.ob-new-modal :deep(.ant-modal-content) { padding: 0; border-radius: 16px; overflow: hidden; }
.ob-new-modal__body { padding: 28px 32px 24px; }
.ob-new-modal__head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.ob-new-modal__title { font-size: 18px; font-weight: 700; color: #0f172a; }
.ob-new-modal__close {
  width: 28px; height: 28px; border-radius: 8px;
  background: #f1f5f9; border: 0; font-size: 18px; color: #64748b; cursor: pointer;
}
.ob-new-modal__close:hover { background: #e2e8f0; color: #0f172a; }

.ob-new-steps {
  display: flex; gap: 12px; margin-bottom: 24px;
  padding: 16px; background: #f8fafc; border-radius: 12px;
}
.ob-new-step {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;
  position: relative;
}
.ob-new-step:not(:last-child)::after {
  content: ''; position: absolute; top: 14px; right: -50%;
  width: 100%; height: 2px; background: #e2e8f0;
}
.ob-new-step--done:not(:last-child)::after,
.ob-new-step--active:not(:last-child)::after {
  background: linear-gradient(90deg, #4f46e5 0%, #e2e8f0 100%);
}
.ob-new-step__circle {
  width: 28px; height: 28px; border-radius: 50%;
  background: #fff; border: 2px solid #cbd5e1; color: #94a3b8;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 12px; z-index: 1;
}
.ob-new-step--active .ob-new-step__circle {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  border-color: transparent; color: #fff;
  box-shadow: 0 4px 12px -2px rgba(79, 70, 229, 0.4);
}
.ob-new-step--done .ob-new-step__circle {
  background: #4f46e5; border-color: #4f46e5; color: #fff;
}
.ob-new-step__label {
  font-size: 12px; color: #64748b; font-weight: 500;
}
.ob-new-step--active .ob-new-step__label { color: #4f46e5; font-weight: 600; }

.ob-new-step-body { min-height: 280px; padding: 8px 0 16px; }
.ob-form-row { margin-bottom: 16px; }
.ob-label { display: block; font-size: 13px; color: #475569; margin-bottom: 8px; font-weight: 500; }
.ob-label .req { color: #ef4444; }
.ob-error { color: #ef4444; font-size: 12px; margin-top: 6px; }
.ob-quick-box { padding: 14px 16px; background: #f8fafc; border-radius: 10px; }
.ob-quick-title { font-size: 12px; color: #94a3b8; margin-bottom: 10px; font-weight: 500; }
.ob-quick-list { display: flex; flex-wrap: wrap; gap: 8px; }
.ob-quick-chip {
  padding: 6px 12px; border-radius: 999px;
  background: #fff; border: 1px solid #e2e8f0;
  color: #475569; font-size: 12px; cursor: pointer;
  transition: all 150ms ease;
}
.ob-quick-chip:hover {
  border-color: #4f46e5; color: #4f46e5;
  background: rgba(79, 70, 229, 0.04);
}

.ob-scene-list { display: grid; gap: 12px; margin-bottom: 16px; }
.ob-scene-option {
  display: flex; align-items: center; gap: 14px;
  padding: 16px; border-radius: 12px;
  background: #fff; border: 2px solid #e2e8f0;
  cursor: pointer; transition: all 150ms ease;
  position: relative;
}
.ob-scene-option:hover { border-color: #cbd5e1; }
.ob-scene-option--active { border-color: #4f46e5; background: rgba(79, 70, 229, 0.04); }
.ob-scene-option--active .ob-scene-option__check { opacity: 1; }
.ob-scene-option__icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 13px; color: #fff;
  flex-shrink: 0;
}
.ob-scene-option--slate .ob-scene-option__icon { background: linear-gradient(135deg, #475569, #1e293b); }
.ob-scene-option--purple .ob-scene-option__icon { background: linear-gradient(135deg, #8b5cf6, #6366f1); }
.ob-scene-option--blue .ob-scene-option__icon { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
.ob-scene-option__main { flex: 1; min-width: 0; }
.ob-scene-option__title { font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 4px; }
.ob-scene-option__desc { font-size: 12px; color: #64748b; line-height: 1.6; margin-bottom: 4px; }
.ob-scene-option__meta { font-size: 11px; color: #94a3b8; }
.ob-scene-option__check {
  width: 24px; height: 24px; border-radius: 50%;
  background: #4f46e5; color: #fff;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 150ms ease;
  flex-shrink: 0;
}

.ob-scene-custom-box { padding-top: 12px; border-top: 1px dashed #e2e8f0; }
.ob-scene-custom-toggle {
  font-size: 13px; color: #4f46e5; font-weight: 500;
  cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
}
.ob-scene-custom-toggle span {
  width: 18px; height: 18px; border-radius: 50%;
  background: rgba(79, 70, 229, 0.12);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 14px; line-height: 1;
}
.ob-scene-custom-form { margin-top: 10px; }

.ob-method-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.ob-method-card {
  padding: 24px; border-radius: 14px;
  background: #fff; border: 2px solid #e2e8f0;
  cursor: pointer; transition: all 150ms ease;
  position: relative; overflow: hidden;
}
.ob-method-card:hover { transform: translateY(-2px); box-shadow: 0 12px 24px -8px rgba(15, 23, 42, 0.12); }
.ob-method-card--blue.ob-method-card--selected {
  border-color: #4f46e5;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.04), transparent);
}
.ob-method-card--green.ob-method-card--selected {
  border-color: #10b981;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.04), transparent);
}
.ob-method-card__icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 14px;
  margin-bottom: 14px;
}
.ob-method-card--blue .ob-method-card__icon { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.ob-method-card--green .ob-method-card__icon { background: linear-gradient(135deg, #10b981, #14b8a6); }
.ob-method-card__tag {
  display: inline-block; padding: 3px 8px; border-radius: 6px;
  background: #f1f5f9; color: #64748b;
  font-size: 11px; font-weight: 500; margin-bottom: 8px;
}
.ob-method-card__title { font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }
.ob-method-card__desc { font-size: 12px; color: #64748b; line-height: 1.6; }

.ob-new-modal__footer {
  display: flex; gap: 8px; align-items: center;
  padding-top: 20px; margin-top: 20px;
  border-top: 1px solid #f1f5f9;
}
</style>
