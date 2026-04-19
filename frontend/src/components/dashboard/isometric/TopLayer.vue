<script setup lang="ts">
const platforms = [
  { id: 'platform:analytics', label: 'ANALYTICS', x: -4.5 },
  { id: 'platform:workflows', label: 'WORKFLOWS', x: 0 },
  { id: 'platform:integrations', label: 'INTEGRATIONS', x: 4.5 },
]
</script>

<template>
  <TresGroup :position="[0, 6, 0]">
    <TresGroup
      v-for="p in platforms"
      :key="p.id"
      :position="[p.x, 0, 0]"
    >
      <TresMesh :name="p.id">
        <TresBoxGeometry :args="[3.5, 0.15, 2.5]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.05" :roughness="0.9" />
      </TresMesh>

      <TresMesh :position="[-0.8, 0.2, 0.4]">
        <TresBoxGeometry :args="[0.6, 0.25, 0.4]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.05" :roughness="0.9" />
      </TresMesh>

      <TresMesh :position="[0.5, 0.2, -0.3]">
        <TresBoxGeometry :args="[0.8, 0.2, 0.5]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.05" :roughness="0.9" />
      </TresMesh>
    </TresGroup>

    <TresMesh :position="[0, 0.25, 0.6]" name="action:btn">
      <TresBoxGeometry :args="[1.2, 0.2, 0.5]" />
      <TresMeshStandardMaterial color="#4ade80" :metalness="0.2" :roughness="0.4" />
    </TresMesh>
  </TresGroup>
</template>
