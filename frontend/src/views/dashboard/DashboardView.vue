<template>
  <div class="dashboard-3d">
    <div class="dashboard-3d__scene">
      <ThreeScene :interaction="interaction" />
    </div>
    <SceneControlPanel
      v-if="interaction.selectedData.value"
      :data="interaction.selectedData.value"
      @deselect="interaction.selectedId.value = null; interaction.selectedData.value = null"
      @override="interaction.applyOverride"
    />
  </div>
</template>

<script setup lang="ts">
import ThreeScene from '../../components/dashboard/ThreeScene.vue'
import SceneControlPanel from '../../components/dashboard/SceneControlPanel.vue'
import { createSceneInteraction } from '../../composables/useSceneInteraction'

const interaction = createSceneInteraction()
</script>

<style scoped>
.dashboard-3d {
  display: flex;
  width: 100%;
  height: 100vh;
  background: #f1f5f9;
  overflow: hidden;
}

.dashboard-3d__scene {
  flex: 1;
  position: relative;
  min-width: 0;
}
</style>
