import client from './client'
import { get } from './client'
import type { ChatMessage, ChatRequest } from '../types'

export const copilotApi = {
  // SSE 流式对话
  async *chatStream(request: ChatRequest): AsyncGenerator<string> {
    const response = await client.post('/copilot/chat', request, {
      responseType: 'stream',
      headers: { Accept: 'text/event-stream' },
      adapter: 'fetch',
    })
    const reader = (response.data as ReadableStream).getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value, { stream: true })
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') return
          yield data
        }
      }
    }
  },

  // 非流式（备用）
  chat(request: ChatRequest) {
    return get<ChatMessage>('/copilot/chat', { params: request })
  },

  history(conversationId: string) {
    return get<ChatMessage[]>(`/copilot/history/${conversationId}`)
  },
}
