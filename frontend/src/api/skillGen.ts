import client from './client'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface SkillDef {
  name?: string
  name_zh?: string
  description?: string
  input_schema?: Record<string, any>
  output_schema?: Record<string, any>
  prompt_template?: string
  tools?: ToolDef[]
  test_cases?: TestCase[]
}

export interface ToolDef {
  name: string
  description: string
  parameters: Record<string, any>
  code: string
  _warnings?: string[]
}

export interface TestCase {
  input: Record<string, any>
  expected_output_contains: string
}

export function createGenSession(assetIds: Record<string, string[]>) {
  return client.post<{ session_id: string; assets_context: string }>('/skill-gen/session', { asset_ids: assetIds })
}

export function skillGenChat(
  sessionId: string,
  message: string,
  onEvent: (ev: { event: string; [key: string]: any }) => void,
  onDone: () => void,
  onError: () => void,
): { abort: () => void } {
  const body = JSON.stringify({ session_id: sessionId, message })
  const ctrl = new AbortController()

  fetch(`${baseURL}/skill-gen/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
    },
    body,
    signal: ctrl.signal,
  }).then(async res => {
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') onDone()
          else { try { onEvent(JSON.parse(data)) } catch (e) { console.warn('SSE 事件解析失败,已跳过', e) } }
        }
      }
    }
    onDone()
  }).catch(() => onError())

  return { abort: () => ctrl.abort() }
}

export function generateSkill(sessionId: string) {
  return client.post<{ skill_def: SkillDef }>('/skill-gen/generate', { session_id: sessionId })
}

export function updateDraft(sessionId: string, draft: Partial<SkillDef>) {
  return client.put(`/skill-gen/draft/${sessionId}`, draft)
}

export function regenerateSection(sessionId: string, section: string, currentDraft: SkillDef) {
  return client.post('/skill-gen/draft/' + sessionId + '/regenerate', { session_id: sessionId, section, current_draft: currentDraft })
}

export function testSkill(skillDef: SkillDef, testInput: Record<string, any>) {
  return client.post<{ results: any[] }>('/skill-gen/test', { skill_def: skillDef, test_input: testInput })
}

export function publishSkill(sessionId: string, changeLog: string, publishedBy: string) {
  return client.post<{ skill_id: string; version: number }>('/skill-gen/publish', {
    session_id: sessionId,
    change_log: changeLog,
    published_by: publishedBy,
  })
}
