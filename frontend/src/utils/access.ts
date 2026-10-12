import type { Permission } from '../types/auth'

/** The same module boundaries are used by routes, navigation and API authorization. */
export function routePermissions(path: string): Permission[] {
  if (path.startsWith('/ops/')) return ['admin:users']
  if (path === '/dashboard' || path.startsWith('/service/mcp')) return ['audit:read']
  if (path.startsWith('/builder')) return ['entity:write']
  if (path === '/agent/manage/new') return ['rule:write']
  if (path.startsWith('/agent/manage')) return ['strategy:read']
  if (path === '/skills/new') return ['rule:write']
  if (path.startsWith('/skills') || path.startsWith('/logic')) return ['rule:read']
  if (path.startsWith('/ontology/') || path.startsWith('/data/')) return ['entity:read']
  return []
}

export function canAccessRoute(path: string, hasPermission: (permission: Permission) => boolean): boolean {
  const permissions = routePermissions(path)
  return !permissions.length || permissions.some(hasPermission)
}

export function firstAccessibleRoute(hasPermission: (permission: Permission) => boolean): string {
  return ['/ontology/list', '/agent/manage', '/skills', '/dashboard', '/ops/config'].find(path => canAccessRoute(path, hasPermission)) || '/forbidden'
}
