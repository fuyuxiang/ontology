import type { Tier } from './ontology'

export interface ActionButton {
  name: string
  action_name: string
  params: Record<string, unknown>
  description: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: string
  reasoningSteps?: ReasoningStep[]
  relatedObjects?: RelatedObject[]
  suggestions?: string[]
  toolRuns?: ToolRun[]
  actions?: ActionButton[]
}

export interface ReasoningStep {
  type: 'ontology' | 'ml' | 'rule' | 'output'
  title: string
  source: string
  result: string
}

export interface RelatedObject {
  id: string
  name: string
  tier: Tier
}

export interface ChatRequest {
  message: string
  contextEntityId?: string
  conversationId?: string
}

export interface ToolRun {
  tool: string
  arguments: Record<string, unknown>
  summary: string
  resultCount: number
}

export interface AgentSSEEvent {
  type: 'tool_start' | 'tool_result' | 'answer'
  tool?: string
  arguments?: Record<string, unknown>
  summary?: string
  resultCount?: number
  content?: string
  suggestions?: string[]
  actions?: ActionButton[]
  toolRuns?: ToolRun[]
}
