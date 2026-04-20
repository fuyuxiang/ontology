// ── 设计态 (Design-Time) ─────────────────────────────────

export interface DesignNodeData {
  nodeType: string
  label: string
  color: string
  icon: string
  description?: string
  config: Record<string, any>
}

export interface WorkflowApp {
  id: string
  code: string
  name: string
  description: string | null
  status: 'draft' | 'published'
  scene_code: string | null
  published_version: number
  canvas_json: { nodes: any[]; edges: any[]; viewport?: any } | null
  published_json: PublishedApp | null
  created_at: string | null
  updated_at: string | null
}

export interface AppBrief {
  id: string
  code: string
  name: string
  description: string | null
  status: string
  scene_code: string | null
  published_version: number
  created_at: string | null
  updated_at: string | null
}

export interface AppCreate {
  code: string
  name: string
  description?: string
  scene_code?: string
  canvas_json?: Record<string, any>
}

export interface AppUpdate {
  name?: string
  description?: string
  scene_code?: string
  canvas_json?: Record<string, any>
}

// ── 运行态 (Run-Time) ───────────────────────────────────

export interface PublishedApp {
  appId: string
  appCode: string
  appName: string
  sceneCode: string | null
  ontologyScope: string[]
  defaultAgent: AgentConfig | null
  toolBindings: ToolBinding[]
  approvalPolicy: ApprovalPolicy
  widgetBindings: WidgetBinding[]
  version: number
}

export interface AgentConfig {
  nodeId: string
  persona: string
  objective: string
  maxSteps: number
  boundTools: string[]
}

export interface ToolBinding {
  name: string
  description: string
  sensitive: boolean
  parameters: Record<string, any>
  required: string[]
}

export interface ApprovalPolicy {
  sensitiveTools: string[]
  requireApproval: boolean
}

export interface WidgetBinding {
  widgetType: string
  nodeId: string
  label: string
  boundAgentNodeId: string | null
}

// ── 工具注册 ─────────────────────────────────────────────

export interface ToolSpec {
  name: string
  description: string
  sensitive: boolean
  parameters: Record<string, any>
  required: string[]
}

// ── 审批 ─────────────────────────────────────────────────

export interface ApprovalTask {
  id: string
  app_id: string
  session_id: string
  tool_name: string
  tool_args: Record<string, any> | null
  status: 'pending' | 'approved' | 'rejected'
  created_by: string
  resolved_by: string | null
  created_at: string | null
  resolved_at: string | null
}

// ── 运行时上下文 ─────────────────────────────────────────

export interface ChatRuntimeContext {
  sceneCode: string
  ontologyType: string
  objectId?: string
  tenantId?: string
  userId?: string
  extra?: Record<string, any>
}
