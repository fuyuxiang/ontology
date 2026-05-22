<template>
  <Teleport to="body">
    <transition name="narrator-fade">
      <div v-if="visible" class="narrator-overlay" @click.self="emit('close')">
        <div class="narrator-card">
          <header class="narrator-card__head">
            <div class="narrator-card__title">
              <span class="narrator-card__icon">⚡</span>
              <span class="narrator-card__name">AI 业务解读</span>
              <span class="narrator-card__obj">{{ displayName }}</span>
              <span class="narrator-card__source" v-if="source">
                {{ source === 'llm' ? '大模型生成' : '本地解读' }}
              </span>
            </div>
            <button class="narrator-card__close" @click="emit('close')">×</button>
          </header>

          <div class="narrator-card__body" ref="bodyRef">
            <p v-if="loading && !displayText" class="narrator-card__loading">正在生成解读...</p>
            <p v-else class="narrator-card__text">
              {{ displayText }}
              <span v-if="loading || typing" class="narrator-card__cursor">▌</span>
            </p>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { studioApi } from '../../api/studio'
import type { StudioObjectType } from '../../api/studio'

const props = defineProps<{
  visible: boolean
  obj: StudioObjectType | null
  relCount?: number
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

const loading = ref(false)
const typing = ref(false)
const fullText = ref('')
const displayText = ref('')
const source = ref<'llm' | 'fallback' | ''>('')
const bodyRef = ref<HTMLElement | null>(null)
let typeTimer: number | undefined
let abortCtl: AbortController | null = null

const displayName = ref('')

function clearTimers() {
  if (typeTimer) { window.clearInterval(typeTimer); typeTimer = undefined }
  abortCtl?.abort()
  abortCtl = null
}

async function fetchExplain() {
  if (!props.obj) return
  clearTimers()
  loading.value = true
  fullText.value = ''
  displayText.value = ''
  source.value = ''
  displayName.value = props.obj.displayName

  abortCtl = new AbortController()
  try {
    const res = await studioApi.narratorExplain({
      apiName: props.obj.apiName,
      displayName: props.obj.displayName,
      tier: props.obj.tier,
      instanceCount: props.obj.aboxScale,
      propCount: props.obj.properties.length,
      relCount: props.relCount ?? 0,
      ruleCount: props.obj.ruleCount,
      actionCount: props.obj.actionCount,
    })
    if (abortCtl?.signal.aborted) return
    source.value = res.source
    fullText.value = res.content
    typewriter()
  } catch (e) {
    if (!abortCtl?.signal.aborted) {
      console.error('narrator failed', e)
      fullText.value = '抱歉，生成解读时遇到问题。'
      typewriter()
    }
  } finally {
    loading.value = false
  }
}

function typewriter() {
  typing.value = true
  let i = 0
  typeTimer = window.setInterval(() => {
    if (i >= fullText.value.length) {
      window.clearInterval(typeTimer!)
      typeTimer = undefined
      typing.value = false
      return
    }
    i++
    displayText.value = fullText.value.slice(0, i)
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }, 25)
}

watch(() => [props.visible, props.obj?.apiName], ([v]) => {
  if (v && props.obj) fetchExplain()
  else clearTimers()
})

onBeforeUnmount(clearTimers)
</script>

<style scoped>
.narrator-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.32);
  backdrop-filter: blur(2px);
  z-index: 9000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 24px;
}

.narrator-card {
  width: 100%;
  max-width: 880px;
  background: rgba(240, 246, 255, 0.92);
  backdrop-filter: blur(20px) saturate(130%);
  border: 1px solid rgba(0, 50, 145, 0.18);
  border-radius: 14px;
  box-shadow:
    0 12px 36px rgba(0, 30, 100, 0.22),
    0 1px 0 rgba(255, 255, 255, 0.6) inset;
  overflow: hidden;
  position: relative;
}
.narrator-card::before {
  content: '';
  position: absolute;
  top: 0; left: 24px; right: 24px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 80, 234, 0.25), transparent);
}

.narrator-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px 10px;
  border-bottom: 1px solid rgba(0, 50, 145, 0.08);
}

.narrator-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #1e293b;
}

.narrator-card__icon {
  font-size: 14px;
  color: #f59e0b;
}

.narrator-card__name {
  font-weight: 700;
  color: #0f172a;
}

.narrator-card__obj {
  background: rgba(15, 81, 234, 0.1);
  color: #1d4ed8;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  margin-left: 4px;
}

.narrator-card__source {
  font-size: 10px;
  color: #94a3b8;
  font-family: monospace;
  margin-left: auto;
  padding-right: 8px;
}

.narrator-card__close {
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  font-size: 22px;
  color: #64748b;
  cursor: pointer;
  border-radius: 6px;
  line-height: 1;
}
.narrator-card__close:hover { background: rgba(0,0,0,0.05); color: #1e293b; }

.narrator-card__body {
  padding: 14px 20px 18px;
  max-height: 280px;
  overflow-y: auto;
}

.narrator-card__loading {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
  font-style: italic;
}

.narrator-card__text {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: #1e293b;
  letter-spacing: 0.2px;
  white-space: pre-wrap;
}

.narrator-card__cursor {
  display: inline-block;
  color: #1d4ed8;
  font-weight: 700;
  animation: narrator-blink 0.8s infinite;
}

@keyframes narrator-blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

.narrator-fade-enter-active, .narrator-fade-leave-active {
  transition: opacity 0.2s;
}
.narrator-fade-enter-active .narrator-card,
.narrator-fade-leave-active .narrator-card {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.narrator-fade-enter-from, .narrator-fade-leave-to { opacity: 0; }
.narrator-fade-enter-from .narrator-card,
.narrator-fade-leave-to .narrator-card {
  transform: translateY(20px);
}
</style>
