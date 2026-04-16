<script setup lang="ts">
import { computed } from 'vue'
import { useSceneState } from '../../../composables/useSceneState'

const props = withDefaults(defineProps<{
  id: string
  position?: [number, number, number]
  size?: [number, number, number]
  selectionType?: 'platform' | 'capsule' | 'entity'
}>(), {
  position: () => [0, 0, 0],
  size: () => [4, 0.15, 3],
  selectionType: 'platform',
})

const { selectedId, hoveredId, select, hover } = useSceneState()

const isSelected = computed(() => selectedId.value === props.id)
const isHovered = computed(() => hoveredId.value === props.id)

const edgeColor = computed(() => {
  if (isSelected.value) return '#22c55e'
  if (isHovered.value) return '#4ade80'
  return '#1a1a1a'
})

function onClick() {
  select(props.id, props.selectionType)
}
</script>

<template>
  <TresGroup :position="position">
    <TresMesh
      @click="onClick"
      @pointer-enter="hover(id)"
      @pointer-leave="hover(null)"
    >
      <TresBoxGeometry :args="size" />
      <TresMeshStandardMaterial
        color="#ffffff"
        :metalness="0.05"
        :roughness="0.9"
      />
    </TresMesh>
    <!-- Edge wireframe -->
    <TresLineSegments>
      <TresEdgesGeometry :args="[null, 15]" />
      <TresLineBasicMaterial
        :color="edgeColor"
        :linewidth="isHovered || isSelected ? 2 : 1"
      />
    </TresLineSegments>
  </TresGroup>
</template>
