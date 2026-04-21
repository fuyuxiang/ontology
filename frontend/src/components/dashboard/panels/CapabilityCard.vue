<template>
  <div class="cap-card" :style="{ flex: flex }">
    <img class="cap-card__bg" :src="bg" alt="" />
    <div class="cap-card__content">
      <img v-if="icon" class="cap-card__icon" :src="icon" alt="" />
      <div class="cap-card__items">
        <span v-for="(item, i) in items" :key="i" class="cap-card__item">{{ item }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  bg: string
  icon?: string
  flex: number
  items: string[]
}>()
</script>

<style scoped>
.cap-card {
  position: relative;
  min-width: 0;
  width: 0;
}
.cap-card__bg {
  width: 100%;
  height: auto;
  display: block;
  object-fit: contain;
}
.cap-card__content {
  position: absolute;
  inset: 15% 10% 20% 10%;
  display: flex;
  align-items: center;
  gap: 8px;
}
.cap-card__icon {
  width: 3.4vw;
  height: auto;
  flex-shrink: 0;
}
.cap-card__items {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: center;
}
.cap-card__item {
  color: #1a3a7a;
  font-size: 0.6vw;
  font-family: AlimamaFangYuanTiVF-Regular, sans-serif;
  white-space: nowrap;
  padding: 0.15vw 0.4vw;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(0, 80, 200, 0.25);
  border-radius: 3px;
  transition: background .15s;
  text-shadow: none;
}
.cap-card__item:hover {
  background: rgba(255, 255, 255, 0.75);
}
</style>
