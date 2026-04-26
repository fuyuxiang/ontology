<template>
  <div class="cap-card" :style="{ flex: flex }" :data-card-key="cardKey">
    <img class="cap-card__bg" :src="bg" alt="" />
    <div class="cap-card__content" :class="{ 'cap-card__content--icon-grid': iconItems?.length }">
      <div v-if="iconItems?.length" class="cap-card__icon-grid" :class="{ 'cap-card__icon-grid--row': iconItems.length <= 3, 'cap-card__icon-grid--six': iconItems.length >= 6 }">
        <div v-for="item in iconItems" :key="item.label" class="cap-card__icon-item">
          <img class="cap-card__icon-item-img" :src="item.icon" :alt="item.label" />
          <span class="cap-card__icon-item-label">{{ item.label }}</span>
        </div>
      </div>
      <template v-else>
        <img v-if="icon" class="cap-card__icon" :src="icon" alt="" />
        <div class="cap-card__items">
          <span v-for="(item, i) in items" :key="i" class="cap-card__item">{{ item }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  cardKey?: string
  bg: string
  icon?: string
  flex: number
  items: string[]
  iconItems?: { icon: string; label: string }[]
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
.cap-card__content--icon-grid {
  inset: 0 7% 43% 7%;
  justify-content: center;
}
.cap-card__icon {
  width: 3.4vw;
  height: auto;
  flex-shrink: 0;
}
.cap-card__items {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 8px;
  align-items: center;
}
.cap-card__item {
  color: var(--semantic-900);
  font-size: 0.6vw;
  font-family: var(--font-sans);
  white-space: nowrap;
  padding: 0.15vw 0.4vw;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(76, 110, 245, 0.2);
  border-radius: 3px;
  transition: background .15s;
  text-shadow: none;
}
.cap-card__item:hover {
  background: rgba(255, 255, 255, 0.75);
}
.cap-card__icon-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  row-gap: 0.02vw;
  column-gap: 0.2vw;
  align-items: end;
}
.cap-card__icon-item {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.06vw;
}
.cap-card__icon-item:nth-child(1) { grid-column: 2 / span 2; grid-row: 1; }
.cap-card__icon-item:nth-child(2) { grid-column: 4 / span 2; grid-row: 1; }
.cap-card__icon-item:nth-child(3) { grid-column: 1 / span 2; grid-row: 2; }
.cap-card__icon-item:nth-child(4) { grid-column: 3 / span 2; grid-row: 2; }
.cap-card__icon-item:nth-child(5) { grid-column: 5 / span 2; grid-row: 2; }
/* 6-item layout: 3+3 grid */
.cap-card__icon-item:nth-child(6) { grid-column: 5 / span 2; grid-row: 2; }
.cap-card__icon-item:nth-child(6) ~ .placeholder { display: none; }
.cap-card__icon-grid--six .cap-card__icon-item:nth-child(1) { grid-column: 1 / span 2; grid-row: 1; }
.cap-card__icon-grid--six .cap-card__icon-item:nth-child(2) { grid-column: 3 / span 2; grid-row: 1; }
.cap-card__icon-grid--six .cap-card__icon-item:nth-child(3) { grid-column: 5 / span 2; grid-row: 1; }
.cap-card__icon-grid--six .cap-card__icon-item:nth-child(4) { grid-column: 1 / span 2; grid-row: 2; }
.cap-card__icon-grid--six .cap-card__icon-item:nth-child(5) { grid-column: 3 / span 2; grid-row: 2; }
.cap-card__icon-grid--six .cap-card__icon-item:nth-child(6) { grid-column: 5 / span 2; grid-row: 2; }
.cap-card__icon-grid--row {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 1.2vw;
}
.cap-card__icon-grid--row .cap-card__icon-item {
  grid-column: unset;
  grid-row: unset;
}
.cap-card__icon-item-img {
  width: clamp(16px, 1.8vw, 36px);
  height: auto;
  display: block;
  filter: drop-shadow(0 0 8px rgba(76, 110, 245, 0.2));
}
.cap-card__icon-item-label {
  max-width: 100%;
  color: var(--semantic-900);
  font-size: clamp(8px, 0.48vw, 11px);
  font-family: var(--font-sans);
  line-height: 1.1;
  white-space: nowrap;
  text-align: center;
  text-shadow: none;
}
</style>
