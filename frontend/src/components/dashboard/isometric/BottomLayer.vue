<script setup lang="ts">
</script>

<template>
  <TresGroup :position="[0, -2, 0]">
    <!-- DATA platform -->
    <TresGroup :position="[-2.5, 0, 0]">
      <TresMesh name="platform:data">
        <TresBoxGeometry :args="[4, 0.15, 3]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.05" :roughness="0.9" />
      </TresMesh>

      <TresMesh v-for="i in 3" :key="`db-${i}`" :position="[-1.2 + (i - 1) * 1.2, 0.35, 0]">
        <TresCylinderGeometry :args="[0.3, 0.3, 0.5, 16]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.05" :roughness="0.9" />
      </TresMesh>
    </TresGroup>

    <!-- MODELS platform -->
    <TresGroup :position="[2.5, 0, 0]">
      <TresMesh name="platform:models">
        <TresBoxGeometry :args="[4, 0.15, 3]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.05" :roughness="0.9" />
      </TresMesh>

      <TresMesh :position="[-0.6, 0.3, 0]">
        <TresTorusGeometry :args="[0.35, 0.08, 8, 6]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.1" :roughness="0.8" />
      </TresMesh>

      <TresMesh :position="[0.6, 0.3, 0]">
        <TresOctahedronGeometry :args="[0.3]" />
        <TresMeshStandardMaterial color="#ffffff" :metalness="0.1" :roughness="0.8" />
      </TresMesh>
    </TresGroup>
  </TresGroup>
</template>
