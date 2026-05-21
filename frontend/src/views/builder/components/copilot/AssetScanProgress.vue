<template>
  <div class="scan-process">
    <div class="scan-process-title">
      <span style="color:#6366f1">🔎</span>
      <span>AI 资产扫描引擎</span>
    </div>
    <div class="scan-steps">
      <div
        v-for="(s, idx) in SCAN_STEPS"
        :key="s.key"
        :class="['scan-step', stepStatus(idx)]"
      >
        <div class="scan-step-indicator">
          <span v-if="stepStatus(idx) === 'done'" style="color:#10b981;font-size:16px">✓</span>
          <span v-else-if="stepStatus(idx) === 'running'" style="color:#6366f1;font-size:14px">⟳</span>
          <span v-else class="scan-step-num">{{ idx + 1 }}</span>
          <div v-if="idx < SCAN_STEPS.length - 1" :class="['scan-step-line', { done: stepStatus(idx) === 'done' }]"></div>
        </div>
        <div class="scan-step-body">
          <div class="scan-step-label">
            <span class="scan-step-icon">{{ stepIcon(idx) }}</span>
            {{ s.label }}
          </div>
          <div v-if="stepStatus(idx) === 'running'" class="scan-step-desc">{{ s.description }}</div>
          <div v-else-if="stepStatus(idx) === 'done'" class="scan-step-result">{{ stepResult(idx) }}</div>
        </div>
      </div>
    </div>

    <div v-if="showRadar" class="radar-container">
      <div class="radar-ring radar-ring-1"></div>
      <div class="radar-ring radar-ring-2"></div>
      <div class="radar-ring radar-ring-3"></div>
      <div class="radar-sweep"></div>
      <div class="radar-center">
        <span style="font-size:20px;color:#6366f1">📡</span>
      </div>
      <div class="radar-label">
        扫描数据中台资产中... <span class="radar-count">{{ radarCount.toLocaleString() }}</span> 条
      </div>
      <div class="radar-dot" style="top:20%;left:65%;animation-delay:0s"></div>
      <div class="radar-dot" style="top:40%;left:25%;animation-delay:0.5s"></div>
      <div class="radar-dot" style="top:60%;left:70%;animation-delay:1s"></div>
      <div class="radar-dot" style="top:30%;left:45%;animation-delay:1.5s"></div>
      <div class="radar-dot" style="top:55%;left:40%;animation-delay:0.8s"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { SCAN_STEPS } from '../../../../data/builderPresets'

const props = defineProps<{ activeStep: number; keywords?: string[] }>()

function stepStatus(i: number): 'done' | 'running' | 'pending' {
  if (i < props.activeStep) return 'done'
  if (i === props.activeStep) return 'running'
  return 'pending'
}

const ICONS = ['🎯', '🛡️', '🧠', '📡', '📚', '✨']
function stepIcon(i: number) { return ICONS[i] || '•' }

function stepResult(i: number) {
  const kw = (props.keywords || []).join('、') || '场景识别 · 资产匹配'
  switch (i) {
    case 0: return `识别关键词：${kw}`
    case 1: return '检测通过，无敏感内容'
    case 2: return '语义抽取主体、属性、关系候选'
    case 3: return '匹配到结构化资产候选'
    case 4: return '匹配到非结构化文档候选'
    case 5: return '组装资产清单完成'
    default: return ''
  }
}

const showRadar = computed(() => stepStatus(3) === 'running' || stepStatus(4) === 'running')
const radarCount = ref(0)
let timer: number | null = null
onMounted(() => {
  timer = window.setInterval(() => { radarCount.value += Math.floor(Math.random() * 137) + 23 }, 220)
})
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>
