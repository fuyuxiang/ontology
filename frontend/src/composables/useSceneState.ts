import { ref } from 'vue'

export interface NodeOverride {
  color?: string
  label?: string
  y?: number
}

export type SelectionType = 'platform' | 'capsule' | 'entity' | null

const selectedId = ref<string | null>(null)
const selectedType = ref<SelectionType>(null)
const hoveredId = ref<string | null>(null)
// 使用普通 Map 而非 reactive Map，避免 TresJS 渲染循环触发 Vue 更新
const nodeOverrides = new Map<string, NodeOverride>()

export function useSceneState() {
  function select(id: string, type: SelectionType) {
    selectedId.value = id
    selectedType.value = type
  }

  function deselect() {
    selectedId.value = null
    selectedType.value = null
  }

  function hover(id: string | null) {
    hoveredId.value = id
  }

  function setOverride(id: string, override: Partial<NodeOverride>) {
    const existing = nodeOverrides.get(id) ?? {}
    nodeOverrides.set(id, { ...existing, ...override })
  }

  function getOverride(id: string): NodeOverride {
    return nodeOverrides.get(id) ?? {}
  }

  return {
    selectedId,
    selectedType,
    hoveredId,
    nodeOverrides,
    select,
    deselect,
    hover,
    setOverride,
    getOverride,
  }
}
