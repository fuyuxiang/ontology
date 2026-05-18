import client from './client'

export interface AiOntologySession {
  id: string
  phase: 'scenario' | 'materials' | 'clarify' | 'building' | 'done'
  scenario: string
  materials_count: number
  clarify_count: number
  has_result: boolean
}

export interface AiOntologyEvent {
  type: 'phase_change' | 'message' | 'suggestion' | 'build_progress' | 'build_result' | 'thinking' | 'error'
  phase?: string
  content?: string
  done?: boolean
  suggestions?: Array<{ label: string; value: string; required?: boolean }>
  step?: string
  progress?: number
  result?: { entities: any[]; relations: any[] }
  conflicts?: Array<{ entity_name: string; entity_name_cn: string; type: string; message: string }>
  summary?: { entity_count: number; relation_count: number; attr_count: number }
}

export interface TelecomScenario {
  name: string
  description: string
}

export const aiOntologyApi = {
  async createSession(): Promise<AiOntologySession> {
    const res = await client.post('/ai-ontology/sessions')
    return res.data
  },

  async getSession(sessionId: string): Promise<AiOntologySession> {
    const res = await client.get(`/ai-ontology/sessions/${sessionId}`)
    return res.data
  },

  async listScenarios(): Promise<{ scenarios: TelecomScenario[] }> {
    const res = await client.get('/ai-ontology/scenarios')
    return res.data
  },

  sendMessage(
    sessionId: string,
    message: string,
    files: File[] = [],
    onEvent: (event: AiOntologyEvent) => void,
    onError: (err: Error) => void,
  ): AbortController {
    const controller = new AbortController()
    const baseURL = client.defaults.baseURL || '/api/v1'

    ;(async () => {
      try {
        const formData = new FormData()
        formData.append('message', message)
        for (const file of files) {
          formData.append('files', file)
        }

        const token = localStorage.getItem('token')
        const headers: Record<string, string> = {}
        if (token) headers['Authorization'] = `Bearer ${token}`

        const res = await fetch(`${baseURL}/ai-ontology/sessions/${sessionId}/message`, {
          method: 'POST',
          headers,
          body: formData,
          signal: controller.signal,
        })

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`)
        }

        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split('\n')
          buffer = parts.pop() ?? ''
          for (const line of parts) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') return
              try {
                const event = JSON.parse(data) as AiOntologyEvent
                onEvent(event)
              } catch { /* skip malformed */ }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          onError(err as Error)
        }
      }
    })()

    return controller
  },

  triggerBuild(
    sessionId: string,
    onEvent: (event: AiOntologyEvent) => void,
    onError: (err: Error) => void,
  ): AbortController {
    const controller = new AbortController()
    const baseURL = client.defaults.baseURL || '/api/v1'

    ;(async () => {
      try {
        const token = localStorage.getItem('token')
        const headers: Record<string, string> = { 'Content-Type': 'application/json' }
        if (token) headers['Authorization'] = `Bearer ${token}`

        const res = await fetch(`${baseURL}/ai-ontology/sessions/${sessionId}/build`, {
          method: 'POST',
          headers,
          signal: controller.signal,
        })

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`)
        }

        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split('\n')
          buffer = parts.pop() ?? ''
          for (const line of parts) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') return
              try {
                const event = JSON.parse(data) as AiOntologyEvent
                onEvent(event)
              } catch { /* skip malformed */ }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          onError(err as Error)
        }
      }
    })()

    return controller
  },

  async getResult(sessionId: string): Promise<{ entities: any[]; relations: any[] }> {
    const res = await client.get(`/ai-ontology/sessions/${sessionId}/result`)
    return res.data
  },
}
