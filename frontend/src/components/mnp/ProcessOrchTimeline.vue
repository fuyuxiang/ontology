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
.orch-timeline { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; }
.orch-timeline__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.orch-timeline__title { font-size: 14px; font-weight: 600; color: #343a40; }
.exec-btn { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; background: #4c6ef5; color: #fff; transition: all 0.2s; }
.exec-btn:hover:not(:disabled) { background: #4263eb; }
.exec-btn:disabled { opacity: 0.7; cursor: not-allowed; }
.exec-btn--running { background: #f59f00; }
.exec-spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.orch-timeline__track { flex: 1; }

/* Ghost placeholders */
.orch-step--ghost { opacity: 0.35; pointer-events: none; }
.dot--ghost { background: #dee2e6; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; z-index: 1; margin-top: 2px; }

/* Pop-in animation */
.orch-step--pop { animation: popIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
@keyframes popIn {
  from { opacity: 0; transform: scale(0.82) translateY(8px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}

.orch-step { display: flex; gap: 12px; position: relative; padding-bottom: 18px; cursor: pointer; }
.orch-step:last-child { padding-bottom: 0; }
.orch-step--active .orch-step__content { background: #f0f4ff; border-color: #4c6ef5; }
.orch-step--running .orch-step__content { background: #fff8e1; border-color: #f59f00; }
.orch-step--done .orch-step__content { border-left: 2px solid #12b886; }

.orch-step__dot { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; z-index: 1; margin-top: 2px; transition: all 0.3s; }
.orch-step__num { font-size: 12px; font-weight: 700; color: #fff; }
.dot--blue { background: #4c6ef5; }
.dot--green { background: #12b886; }
.dot--orange { background: #f59f00; }
.dot--red { background: #fa5252; }
.dot--purple { background: #7950f2; }
.dot--done { background: #12b886; }
.dot--running { background: #f59f00; animation: pulse 1.2s ease-in-out infinite; }
.dot-pulse { width: 10px; height: 10px; border-radius: 50%; background: #fff; }
@keyframes pulse { 0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(245,159,0,0.4); } 50% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(245,159,0,0); } }

.orch-step__line { position: absolute; left: 13px; top: 30px; bottom: 0; width: 2px; background: #dee2e6; transition: background 0.3s; }
.line--done { background: #12b886; }
.orch-step__content { flex: 1; padding: 8px 12px; border-radius: 8px; border: 1px solid transparent; transition: all 0.2s; }
.orch-step__content:hover { background: #f8f9fa; }
.orch-step__tag-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.orch-step__tag { display: inline-block; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.tag--blue { background: #e7f5ff; color: #1c7ed6; }
.tag--green { background: #e6fcf5; color: #0ca678; }
.tag--orange { background: #fff8e1; color: #e67700; }
.tag--red { background: #fff5f5; color: #e03131; }
.tag--purple { background: #f3f0ff; color: #7048e8; }
.orch-step__duration { font-size: 10px; color: #12b886; font-weight: 600; background: #e6fcf5; padding: 1px 6px; border-radius: 3px; }
.orch-step__status-badge { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 3px; }
.status--running { background: #fff8e1; color: #e67700; animation: fadeInOut 1.2s ease-in-out infinite; }
.status--done { background: #e6fcf5; color: #0ca678; }
@keyframes fadeInOut { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.orch-step__desc { font-size: 12px; color: #495057; line-height: 1.5; margin-bottom: 4px; }
.orch-step__entities { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-bottom: 4px; }
.orch-entity { font-size: 11px; padding: 1px 6px; border-radius: 3px; background: #e7f5ff; color: #1c7ed6; font-family: monospace; }
.orch-entity--out { background: #e6fcf5; color: #0ca678; }
.orch-arrow { color: #4c6ef5; font-weight: 700; font-size: 12px; }
.orch-step__rules, .orch-step__actions { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.rule-chip { font-size: 10px; padding: 1px 6px; border-radius: 3px; background: #fff8e1; color: #e67700; }
.action-chip { font-size: 10px; padding: 1px 6px; border-radius: 3px; background: #e6fcf5; color: #0ca678; }

.orch-progress { margin-top: 14px; padding-top: 12px; border-top: 1px solid #f1f3f5; }
.orch-progress__bar { height: 6px; background: #f1f3f5; border-radius: 3px; overflow: hidden; }
.orch-progress__fill { height: 100%; background: linear-gradient(90deg, #4c6ef5, #12b886); border-radius: 3px; transition: width 0.5s ease; }
.orch-progress__text { font-size: 11px; color: #868e96; margin-top: 4px; text-align: center; }
</style>
