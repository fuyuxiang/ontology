import { computed } from 'vue'
import { useAuthStore } from '../store/auth'
import type { Permission } from '../types/auth'

/** Match the effective permissions returned by the server, including edited roles. */
export function useManagementPermission(permission: Permission = 'entity:write') {
  const auth = useAuthStore()
  return {
    canEdit: computed(() => auth.hasPermission(permission)),
    canDelete: computed(() => auth.hasPermission(permission === 'rule:write' ? 'rule:write' : 'entity:delete')),
    canExecute: computed(() => auth.hasPermission('rule:execute') || auth.hasPermission('rule:write')),
  }
}
