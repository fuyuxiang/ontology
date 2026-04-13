import type { Tier } from './ontology'

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: string
  reasoningSteps?: ReasoningStep[]
  relatedObjects?: RelatedObject[]
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
