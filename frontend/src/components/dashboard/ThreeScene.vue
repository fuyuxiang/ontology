<template>
  <div ref="containerRef" class="three-scene"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { createThreeScene, type ThreeContext } from '../../composables/useThreeScene'
import { buildIsometricScene } from '../../composables/useIsometricScene'
import { type SceneInteraction } from '../../composables/useSceneInteraction'

const props = defineProps<{
  interaction: SceneInteraction
}>()

const containerRef = ref<HTMLElement | null>(null)
let ctx: ThreeContext | null = null

onMounted(() => {
  if (!containerRef.value) return
  ctx = createThreeScene(containerRef.value)
  buildIsometricScene(ctx)
  props.interaction.attach(ctx)
})

onUnmounted(() => {
  props.interaction.detach()
  ctx?.dispose()
  ctx = null
})
</script>

<style scoped>
.three-scene {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
