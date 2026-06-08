<template>
  <div class="ob-shell">
    <header class="ob-shell-topbar">
      <div class="ob-shell-title">
        <span class="name">{{ session.ontologyName }}</span>
        <span class="meta">{{ methodLabel }}<template v-if="session.scenarioName"> · {{ session.scenarioName }}</template></span>
      </div>
      <div class="ob-shell-actions">
        <span class="ob-shell-version">{{ versionLabel }}</span>
      </div>
    </header>

    <div class="ob-steps">
      <template v-for="(step, idx) in stepsForMethod" :key="step.key">
        <div
          class="ob-step"
          :class="{ 'ob-step--active': currentStep === idx + 1, 'ob-step--done': currentStep > idx + 1 }"
          @click="onStepClick(idx + 1)"
        >
          <div class="ob-step-circle">{{ idx + 1 }}</div>
          <div class="ob-step-text">
            <div class="ob-step-title">{{ step.label }}</div>
            <div class="ob-step-sub">{{ step.sub }}</div>
          </div>
        </div>
        <div v-if="idx < stepsForMethod.length - 1" class="ob-step-connector"></div>
      </template>
    </div>

    <div class="ob-shell-body">
      <component
        v-if="currentStep === 1"
        :is="stepOneCmp"
        :session="session"
        @next="goNext"
      />
      <Step2Review
        v-else-if="currentStep === 2"
        :session="session"
        @prev="goPrev"
        @next="goNext"
      />
      <Step3Mapping
        v-else-if="currentStep === 3 && session.buildMethod === 'manual'"
        :session="session"
        @prev="goPrev"
        @next="goNext"
      />
      <Step3Hydrate
        v-else-if="(currentStep === 4 && session.buildMethod === 'manual') || (currentStep === 3 && session.buildMethod !== 'manual')"
        :session="session"
        @prev="goPrev"
        @goto-studio="$emit('goto-studio')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { BuilderSession, BuildMethod } from '../../../types/builder'
import Step1Manual from './Step1Manual.vue'
import Step1Import from './Step1Import.vue'
import Step1Extract from './Step1Extract.vue'
import Step1Build from './Step1Build.vue'
import Step2Review from './Step2Review.vue'
import Step3Mapping from './Step3Mapping.vue'
import Step3Hydrate from './Step3Hydrate.vue'

const props = defineProps<{ session: BuilderSession }>()
defineEmits<{
  (e: 'goto-studio'): void
}>()

const currentStep = ref(1)

const stepOneCmp = computed(() => ({
  manual:  Step1Manual,
  import:  Step1Import,
  extract: Step1Extract,
  chat:    Step1Build,
}[props.session.buildMethod] || Step1Manual))

const METHOD_LABEL: Record<BuildMethod, string> = {
  manual: '手工建模',
  import: '文件导入',
  extract: '文档抽取',
  chat: '对话生成',
}
const methodLabel = computed(() => METHOD_LABEL[props.session.buildMethod] || '手工建模')

const STEP_DEFS: Record<BuildMethod, { key: string; label: string; sub: string }[]> = {
  manual: [
    { key: 'build', label: '手工建模', sub: '逐项录入对象、属性、关系' },
    { key: 'review', label: '专家审批', sub: '逐对象通过 / 修正 / 挂载' },
    { key: 'mapping', label: '数据映射', sub: '数据源绑定 · 属性列映射' },
    { key: 'hydrate', label: '水合演练 · 发布', sub: '基于映射 · 端到端验证' },
  ],
  import: [
    { key: 'import', label: '文件导入', sub: 'OWL / RDF / JSON 标准本体' },
    { key: 'review', label: '导入审核', sub: '逐对象通过 / 修正 / 挂载' },
    { key: 'hydrate', label: '水合演练 · 发布', sub: '版本确认 · 工作室可见' },
  ],
  extract: [
    { key: 'extract', label: '文档抽取', sub: '业务文档 LLM 流式抽取' },
    { key: 'review', label: '专家走测审批', sub: '建议挂载 · 通过' },
    { key: 'hydrate', label: '水合演练 · 发布', sub: '数据接入 · 端到端验证' },
  ],
  chat: [
    { key: 'chat', label: '对话生成', sub: '场景驱动 · 资产联动' },
    { key: 'review', label: '专家走测审批', sub: '建议挂载 · 通过' },
    { key: 'hydrate', label: '水合演练 · 发布', sub: '数据接入 · 端到端验证' },
  ],
}

const stepsForMethod = computed(() => STEP_DEFS[props.session.buildMethod] || STEP_DEFS.manual)

const versionLabel = computed(() => {
  if (props.session.publishedVersion) return `已发布 · ${props.session.publishedVersion}`
  if (props.session.status === 'pending_publish' || props.session.status === 'publishing') return '待发布 · v0.1'
  return '草稿 · v0.1'
})

watch(() => props.session.status, (s) => {
  if (s === 'pending_review' || s === 'reviewing') currentStep.value = Math.max(currentStep.value, 2)
  else if (s === 'pending_hydration' || s === 'hydrating' || s === 'pending_publish' || s === 'publishing' || s === 'published') currentStep.value = 3
})

function onStepClick(n: number) {
  if (n <= currentStep.value) currentStep.value = n
}
function goNext() { currentStep.value = Math.min(stepsForMethod.value.length, currentStep.value + 1) }
function goPrev() { currentStep.value = Math.max(1, currentStep.value - 1) }
</script>

<style scoped>
.ob-shell {
  display: flex; flex-direction: column;
  min-height: calc(100vh - 64px);
  background: #f8fafc;
}
.ob-shell-topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 14px 24px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.ob-shell-title {
  display: flex; flex-direction: column; gap: 2px;
}
.ob-shell-title .name { font-size: 15px; font-weight: 600; color: #0f172a; }
.ob-shell-title .meta { font-size: 12px; color: #94a3b8; }
.ob-shell-actions { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.ob-shell-version {
  display: inline-block; padding: 4px 10px; border-radius: 6px;
  background: rgba(79, 70, 229, 0.08); color: #4f46e5;
  font-size: 12px; font-weight: 500;
}

.ob-steps {
  display: flex; align-items: center;
  padding: 18px 32px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
}
.ob-step {
  display: flex; align-items: center; gap: 10px;
  cursor: pointer; transition: opacity 150ms ease;
}
.ob-step:hover { opacity: 0.85; }
.ob-step-circle {
  width: 28px; height: 28px; border-radius: 50%;
  background: #fff; border: 2px solid #cbd5e1; color: #94a3b8;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 12px; flex-shrink: 0;
  transition: all 150ms ease;
}
.ob-step--active .ob-step-circle {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  border-color: transparent; color: #fff;
  box-shadow: 0 4px 12px -2px rgba(79, 70, 229, 0.4);
}
.ob-step--done .ob-step-circle { background: #4f46e5; border-color: #4f46e5; color: #fff; }
.ob-step-text { line-height: 1.3; }
.ob-step-title { font-size: 13px; font-weight: 600; color: #0f172a; }
.ob-step--active .ob-step-title { color: #4f46e5; }
.ob-step-sub { font-size: 11px; color: #94a3b8; }
.ob-step-connector { flex: 1; height: 2px; background: #e2e8f0; margin: 0 16px; }
.ob-step--done + .ob-step-connector,
.ob-step--active + .ob-step-connector { background: linear-gradient(90deg, #4f46e5, #e2e8f0); }

.ob-shell-body { flex: 1; overflow: hidden; }
</style>
