<template>
  <div class="browser">
    <div class="browser__content">
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.browser__content {
  flex: 1;
  overflow: hidden;
}
</style>
