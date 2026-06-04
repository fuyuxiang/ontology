<template>
  <div class="step-chat">
    <h2 class="step-chat__title">AI 对话细化需求</h2>

    <div class="step-chat__layout">
      <div class="step-chat__sidebar">
        <h3>已选资产</h3>
        <pre class="step-chat__context">{{ props.assetsContext }}</pre>
      </div>

      <div class="step-chat__main">
        <div class="step-chat__messages" ref="msgContainer">
          <div v-for="(msg, i) in messages" :key="i" class="step-chat__msg" :class="'step-chat__msg--' + msg.role">
            <div class="step-chat__msg-content" v-html="msg.content"></div>
          </div>
          <div v-if="streaming" class="step-chat__msg step-chat__msg--assistant">
            <div class="step-chat__msg-content">{{ streamBuffer }}<span class="step-chat__cursor">|</span></div>
          </div>
        </div>

        <div v-if="summaryReady" class="step-chat__summary-bar">
          <span>需求摘要已生成</span>
          <button class="step-chat__gen-btn" :disabled="generating" @click="handleGenerate">
            {{ generating ? '生成中...' : '生成技能草稿' }}
          </button>
        </div>

        <div class="step-chat__input-bar" v-if="!summaryReady">
          <input class="step-chat__input" v-model="input" placeholder="输入消息..." @keyup.enter="send" :disabled="streaming" />
          <button class="step-chat__send" @click="send" :disabled="!input.trim() || streaming">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { skillGenChat, generateSkill, type SkillDef } from '../../../api/skillGen'

const props = defineProps<{ sessionId: string; assetsContext: string }>()
const emit = defineEmits<{ (e: 'next', draft: SkillDef): void }>()

const messages = ref<{ role: string; content: string }[]>([])
const input = ref('')
const streaming = ref(false)
const streamBuffer = ref('')
const summaryReady = ref(false)
const generating = ref(false)
const msgContainer = ref<HTMLElement | null>(null)

function scrollBottom() {
  nextTick(() => { if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight })
}

function send() {
  if (!input.value.trim() || streaming.value) return
  const msg = input.value.trim()
  input.value = ''
  messages.value.push({ role: 'user', content: msg })
  scrollBottom()
  doChat(msg)
}

function doChat(message: string) {
  streaming.value = true
  streamBuffer.value = ''

  skillGenChat(props.sessionId, message,
    (ev) => {
      if (ev.event === 'token') {
        streamBuffer.value += ev.content
        scrollBottom()
      } else if (ev.event === 'summary_ready') {
        summaryReady.value = true
      }
    },
    () => {
      if (streamBuffer.value) {
        messages.value.push({ role: 'assistant', content: streamBuffer.value })
        streamBuffer.value = ''
      }
      streaming.value = false
      scrollBottom()
    },
    () => { streaming.value = false }
  )
}

async function handleGenerate() {
  generating.value = true
  try {
    const resp = await generateSkill(props.sessionId)
    emit('next', resp.data.skill_def)
  } catch { alert('生成失败，请重试') }
  finally { generating.value = false }
}

onMounted(() => {
  doChat('')
})
</script>

<style scoped>
.step-chat__title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.step-chat__layout { display: flex; gap: 16px; height: 500px; }
.step-chat__sidebar { width: 240px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; overflow-y: auto; }
.step-chat__sidebar h3 { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.step-chat__context { font-size: 11px; white-space: pre-wrap; color: #555; line-height: 1.5; }
.step-chat__main { flex: 1; display: flex; flex-direction: column; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.step-chat__messages { flex: 1; overflow-y: auto; padding: 16px; }
.step-chat__msg { margin-bottom: 12px; }
.step-chat__msg--user .step-chat__msg-content { background: #e8f0fe; padding: 10px 14px; border-radius: 10px; font-size: 13px; max-width: 80%; margin-left: auto; }
.step-chat__msg--assistant .step-chat__msg-content { background: #f5f5f5; padding: 10px 14px; border-radius: 10px; font-size: 13px; max-width: 80%; white-space: pre-wrap; }
.step-chat__cursor { animation: blink 1s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.step-chat__summary-bar { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #e6f7e9; border-top: 1px solid #c8e6c9; }
.step-chat__summary-bar span { font-size: 13px; color: #1a8a3a; font-weight: 500; }
.step-chat__gen-btn { padding: 8px 20px; background: #1a8a3a; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.step-chat__gen-btn:disabled { opacity: 0.5; }
.step-chat__input-bar { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid #e0e0e0; }
.step-chat__input { flex: 1; padding: 10px 14px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 13px; }
.step-chat__send { padding: 10px 20px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.step-chat__send:disabled { opacity: 0.5; }
</style>
