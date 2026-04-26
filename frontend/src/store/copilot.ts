import { defineStore } from 'pinia'
import { ref } from 'vue'
import { copilotApi } from '../api/copilot'
import type { ChatMessage, ChatRequest } from '../types'

export const useCopilotStore = defineStore('copilot', () => {
  const messages = ref<ChatMessage[]>([])
  const isTyping = ref(false)
  const conversationId = ref<string | null>(null)

  function addMessage(msg: ChatMessage) {
    messages.value.push(msg)
  }

  async function sendMessage(content: string, contextEntityId?: string) {
    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }
    addMessage(userMsg)

    isTyping.value = true
    const aiMsg: ChatMessage = {
      id: `msg_${Date.now()}_ai`,
      role: 'ai',
      content: '',
      timestamp: new Date().toISOString(),
    }
    addMessage(aiMsg)

    try {
      const request: ChatRequest = {
        message: content,
        contextEntityId,
        conversationId: conversationId.value ?? undefined,
      }
      for await (const chunk of copilotApi.chatStream(request)) {
        try {
          const parsed = JSON.parse(chunk)
          if (parsed.content) aiMsg.content += parsed.content
          if (parsed.reasoningSteps) aiMsg.reasoningSteps = parsed.reasoningSteps
          if (parsed.conversationId) conversationId.value = parsed.conversationId
        } catch {
          aiMsg.content += chunk
        }
      }
    } catch (e: unknown) {
      aiMsg.content = `抱歉，请求失败：${(e as Error).message}`
    } finally {
      isTyping.value = false
    }
  }

  function clearChat() {
    messages.value = []
    conversationId.value = null
  }

  return { messages, isTyping, conversationId, sendMessage, clearChat }
})
