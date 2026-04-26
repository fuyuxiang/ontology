<template>
  <div class="orch-timeline">
    <div class="orch-timeline__header">
      <div class="orch-timeline__title">全流程编排</div>
      <button class="exec-btn" :class="{ 'exec-btn--running': running }" :disabled="running" @click="$emit('startExec')">
        <template v-if="running">
          <span class="exec-spinner"></span> 执行中...
        </template>
        <template v-else-if="allDone">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M1 7h12M7 1v12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          重新执行
        </template>
        <template v-else>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 2l9 5-9 5V2z" fill="currentColor"/></svg>
          启动流程执行
        </template>
      </button>
    </div>

    <div class="orch-timeline__track">
      <!-- 未执行时：显示占位列表 -->
      <template v-if="!hasStarted">
        <div v-for="(step, i) in steps" :key="'ph-'+i" class="orch-step orch-step--ghost">
          <div class="orch-step__dot dot--ghost">
            <span class="orch-step__num">{{ i + 1 }}</span>
          </div>
          <div class="orch-step__line" v-if="i < steps.length - 1"></div>
          <div class="orch-step__content">
            <div class="orch-step__tag-row">
              <div class="orch-step__tag" :class="`tag--${step.color}`" style="opacity:0.45">{{ step.tag }}</div>
            </div>
          </div>
        </div>
      </template>

      <!-- 执行中/完成：节点逐个冒出 -->
      <template v-else>
        <div v-for="(step, i) in steps" :key="'step-'+i"
          v-show="nodeVisible[i]"
          class="orch-step"
          :class="[
            { 'orch-step--active': activeStep === i, 'orch-step--pop': nodeVisible[i] },
            `orch-step--${stepStates[i] || 'pending'}`
          ]"
          @click="$emit('stepClick', i)"
        >
          <div class="orch-step__dot" :class="dotClass(i, step.color)">
            <svg v-if="stepStates[i] === 'done'" width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7l3 3 5-5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span v-else-if="stepStates[i] === 'running'" class="dot-pulse"></span>
            <span v-else class="orch-step__num">{{ i + 1 }}</span>
          </div>
          <div class="orch-step__line" v-if="i < steps.length - 1" :class="{ 'line--done': stepStates[i] === 'done' }"></div>
          <div class="orch-step__content">
            <div class="orch-step__tag-row">
              <div class="orch-step__tag" :class="`tag--${step.color}`">{{ step.tag }}</div>
              <span v-if="stepStates[i] === 'done' && stepDurations[i]" class="orch-step__duration">{{ stepDurations[i] }}s</span>
              <span v-if="stepStates[i] === 'running'" class="orch-step__status-badge status--running">执行中</span>
              <span v-else-if="stepStates[i] === 'done'" class="orch-step__status-badge status--done">已完成</span>
            </div>
            <div class="orch-step__desc">{{ step.desc }}</div>
            <div class="orch-step__entities" v-if="step.inputEntities.length || step.outputEntities.length">
              <span class="orch-entity" v-for="e in step.inputEntities" :key="'in-'+e">{{ e }}</span>
              <span class="orch-arrow" v-if="step.inputEntities.length && step.outputEntities.length">→</span>
              <span class="orch-entity orch-entity--out" v-for="e in step.outputEntities" :key="'out-'+e">{{ e }}</span>
            </div>
            <div class="orch-step__rules" v-if="step.rules.length">
              <span class="rule-chip" v-for="r in step.rules" :key="r">{{ r }}</span>
            </div>
            <div class="orch-step__actions" v-if="step.actions.length">
              <span class="action-chip" v-for="a in step.actions" :key="a">{{ a }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 进度条 -->
    <div class="orch-progress" v-if="running || allDone">
      <div class="orch-progress__bar">
        <div class="orch-progress__fill" :style="{ width: progressPct + '%' }"></div>
      </div>
      <div class="orch-progress__text">{{ doneCount }}/{{ steps.length }} · {{ progressPct }}%</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface OrchStep {
  tag: string
  desc: string
  inputEntities: string[]
  outputEntities: string[]
  rules: string[]
  actions: string[]
  color: 'blue' | 'green' | 'orange' | 'red' | 'purple'
}

export type StepState = 'pending' | 'running' | 'done'

const props = defineProps<{
  steps: OrchStep[]
  activeStep: number
  stepStates: StepState[]
  stepDurations: (string | null)[]
  running: boolean
}>()
defineEmits<{ stepClick: [i: number]; startExec: [] }>()

const doneCount = computed(() => props.stepStates.filter(s => s === 'done').length)
const allDone = computed(() => doneCount.value === props.steps.length && props.steps.length > 0)
const progressPct = computed(() => Math.round((doneCount.value / props.steps.length) * 100))

/* -------- NODE VISIBILITY -------- */
const hasStarted = ref(false)
const nodeVisible = ref<boolean[]>([])

watch(() => props.steps.length, (n) => {
  nodeVisible.value = Array(n).fill(false)
}, { immediate: true })

watch(
  () => props.stepStates.map(s => s),
  (states, oldStates) => {
    states.forEach((state, i) => {
      const prev = oldStates?.[i]
      // Node pops in the moment it becomes running
      if (state === 'running' && !nodeVisible.value[i]) {
        hasStarted.value = true
        nodeVisible.value[i] = true
        nodeVisible.value = [...nodeVisible.value]
      }
      // On re-run: reset
      if (state === 'pending' && prev !== 'pending') {
        nodeVisible.value[i] = false
        nodeVisible.value = [...nodeVisible.value]
        if (i === 0) hasStarted.value = false
      }
    })
  },
  { deep: true }
)

function dotClass(i: number, color: string) {
  if (props.stepStates[i] === 'done') return 'dot--done'
  if (props.stepStates[i] === 'running') return 'dot--running'
  return `dot--${color}`
}
</script>

<style scoped>
.orch-timeline { background: var(--neutral-0); border-radius: 10px; border: 1px solid var(--neutral-200); padding: 16px; overflow-y: auto; display: flex; flex-direction: column; }
.orch-timeline__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.orch-timeline__title { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.exec-btn { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 8px; font-size: var(--text-body-size); font-weight: 600; cursor: pointer; border: none; background: var(--semantic-600); color: var(--neutral-0); transition: all 0.2s; }
.exec-btn:hover:not(:disabled) { background: var(--semantic-700); }
.exec-btn:disabled { opacity: 0.7; cursor: not-allowed; }
.exec-btn--running { background: var(--kinetic-500); }
.exec-spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: var(--neutral-0); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.orch-timeline__track { flex: 1; }

/* Ghost placeholders */
.orch-step--ghost { opacity: 0.35; pointer-events: none; }
.dot--ghost { background: var(--neutral-300); width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; z-index: 1; margin-top: 2px; }

/* Pop-in animation */
.orch-step--pop { animation: popIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
@keyframes popIn {
  from { opacity: 0; transform: scale(0.82) translateY(8px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}

.orch-step { display: flex; gap: 12px; position: relative; padding-bottom: 18px; cursor: pointer; }
.orch-step:last-child { padding-bottom: 0; }
.orch-step--active .orch-step__content { background: var(--semantic-50); border-color: var(--semantic-600); }
.orch-step--running .orch-step__content { background: var(--status-warning-bg); border-color: var(--kinetic-500); }
.orch-step--done .orch-step__content { border-left: 2px solid var(--status-success); }

.orch-step__dot { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; z-index: 1; margin-top: 2px; transition: all 0.3s; }
.orch-step__num { font-size: var(--text-code-size); font-weight: 700; color: var(--neutral-0); }
.dot--blue { background: var(--semantic-600); }
.dot--green { background: var(--status-success); }
.dot--orange { background: var(--kinetic-500); }
.dot--red { background: var(--status-error); }
.dot--purple { background: var(--tier2-primary); }
.dot--done { background: var(--status-success); }
.dot--running { background: var(--kinetic-500); animation: pulse 1.2s ease-in-out infinite; }
.dot-pulse { width: 10px; height: 10px; border-radius: 50%; background: var(--neutral-0); }
@keyframes pulse { 0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(245,159,0,0.4); } 50% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(245,159,0,0); } }

.orch-step__line { position: absolute; left: 13px; top: 30px; bottom: 0; width: 2px; background: var(--neutral-300); transition: background 0.3s; }
.line--done { background: var(--status-success); }
.orch-step__content { flex: 1; padding: 8px 12px; border-radius: 8px; border: 1px solid transparent; transition: all 0.2s; }
.orch-step__content:hover { background: var(--neutral-50); }
.orch-step__tag-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.orch-step__tag { display: inline-block; font-size: var(--text-code-size); font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.tag--blue { background: var(--status-info-bg); color: var(--status-info); }
.tag--green { background: var(--status-success-bg); color: var(--dynamic-700); }
.tag--orange { background: var(--status-warning-bg); color: var(--kinetic-700); }
.tag--red { background: var(--status-error-bg); color: var(--status-error); }
.tag--purple { background: var(--tier2-bg); color: var(--tier2-primary); }
.orch-step__duration { font-size: var(--text-caption-upper-size); color: var(--status-success); font-weight: 600; background: var(--status-success-bg); padding: 1px 6px; border-radius: 3px; }
.orch-step__status-badge { font-size: var(--text-caption-upper-size); font-weight: 600; padding: 1px 6px; border-radius: 3px; }
.status--running { background: var(--status-warning-bg); color: var(--kinetic-700); animation: fadeInOut 1.2s ease-in-out infinite; }
.status--done { background: var(--status-success-bg); color: var(--dynamic-700); }
@keyframes fadeInOut { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.orch-step__desc { font-size: var(--text-code-size); color: var(--neutral-700); line-height: 1.5; margin-bottom: 4px; }
.orch-step__entities { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-bottom: 4px; }
.orch-entity { font-size: var(--text-caption-size); padding: 1px 6px; border-radius: 3px; background: var(--status-info-bg); color: var(--status-info); font-family: var(--font-mono); }
.orch-entity--out { background: var(--status-success-bg); color: var(--dynamic-700); }
.orch-arrow { color: var(--semantic-600); font-weight: 700; font-size: var(--text-code-size); }
.orch-step__rules, .orch-step__actions { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.rule-chip { font-size: var(--text-caption-upper-size); padding: 1px 6px; border-radius: 3px; background: var(--status-warning-bg); color: var(--kinetic-700); }
.action-chip { font-size: var(--text-caption-upper-size); padding: 1px 6px; border-radius: 3px; background: var(--status-success-bg); color: var(--dynamic-700); }

.orch-progress { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--neutral-100); }
.orch-progress__bar { height: 6px; background: var(--neutral-100); border-radius: 3px; overflow: hidden; }
.orch-progress__fill { height: 100%; background: linear-gradient(90deg, #4c6ef5, #12b886); border-radius: 3px; transition: width 0.5s ease; }
.orch-progress__text { font-size: var(--text-caption-size); color: var(--neutral-600); margin-top: 4px; text-align: center; }
</style>
