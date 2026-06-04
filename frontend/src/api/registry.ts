import { get } from './client'

export interface RegistryItem {
  id: string
  type: 'rule' | 'function'
  name: string
  callable_name: string
  description: string
  entity_id: string | null
  entity_name: string
  tags: string[]
  input_params: Record<string, any>[]
  output_info: string
  ref_count: number
}

export interface RegistryGroup {
  entity_id: string | null
  entity_name: string
  items: RegistryItem[]
}

export interface RefInfo {
  type: string
  id: string
  name: string
}

export const registryApi = {
  listItems(query?: { type?: string; entity_id?: string; search?: string; tags?: string[] }) {
    return get<RegistryItem[]>('/registry/items', { params: query })
  },

  listGrouped(search?: string) {
    return get<RegistryGroup[]>('/registry/grouped', { params: { search } })
  },

  getRefs(itemType: string, itemId: string) {
    return get<{ item_id: string; item_type: string; references: RefInfo[] }>(`/registry/refs/${itemType}/${itemId}`)
  },
}
