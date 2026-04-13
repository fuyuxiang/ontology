export type Role = 'admin' | 'editor' | 'operator' | 'viewer'

export type Permission =
  | 'entity:read' | 'entity:write' | 'entity:delete'
  | 'rule:read' | 'rule:write' | 'rule:execute'
  | 'strategy:read' | 'strategy:execute'
  | 'audit:read'
  | 'admin:users'

export interface User {
  id: string
  username: string
  name: string
  role: Role
  permissions: Permission[]
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  user: User
}

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  admin: ['entity:read', 'entity:write', 'entity:delete', 'rule:read', 'rule:write', 'rule:execute', 'strategy:read', 'strategy:execute', 'audit:read', 'admin:users'],
  editor: ['entity:read', 'entity:write', 'rule:read', 'rule:write', 'strategy:read', 'audit:read'],
  operator: ['entity:read', 'rule:read', 'rule:execute', 'strategy:read', 'strategy:execute', 'audit:read'],
  viewer: ['entity:read', 'rule:read', 'strategy:read'],
}
