<script setup lang="ts">
const props = withDefaults(defineProps<{
  id: string
  label: string
  position?: [number, number, number]
}>(), {
  position: () => [0, 0, 0],
})
</script>

<template>
  <TresGroup :position="position">
    <TresMesh :rotation-z="Math.PI / 2" :name="id">
      <TresCapsuleGeometry :args="[0.15, 0.5, 8, 16]" />
      <TresMeshStandardMaterial color="#4ade80" :metalness="0.2" :roughness="0.4" />
    </TresMesh>
    <TresGroup :position="[0, 0.4, 0]">
      <TresMesh>
        <TresPlaneGeometry :args="[label.length * 0.12 + 0.3, 0.25]" />
        <TresMeshBasicMaterial color="#ffffff" :opacity="0.92" transparent />
      </TresMesh>
    </TresGroup>
  </TresGroup>
</template>
