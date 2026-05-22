<template>
  <div class="marketplace">
    <header class="marketplace__header">
      <div class="marketplace__title">
        <h1>本体原料集市</h1>
        <span class="marketplace__subtitle">资产管理 · 数据原料登记与水合追踪</span>
      </div>
      <div class="marketplace__actions">
        <button class="marketplace__btn" @click="openInNewWindow">
          <span class="marketplace__btn-icon">↗</span>
          新窗口打开
        </button>
        <button class="marketplace__btn" @click="reload">
          <span class="marketplace__btn-icon">⟳</span>
          刷新
        </button>
      </div>
    </header>

    <div class="marketplace__body">
      <iframe
        ref="iframeRef"
        :src="iframeSrc"
        title="本体原料集市"
        class="marketplace__iframe"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const iframeRef = ref<HTMLIFrameElement | null>(null)
const iframeSrc = ref('/fttr-pages/marketplace.html')

function reload() {
  if (iframeRef.value) {
    iframeRef.value.src = iframeRef.value.src
  }
}

function openInNewWindow() {
  window.open(iframeSrc.value, '_blank')
}
</script>

<style scoped>
.marketplace {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8fafc;
}

.marketplace__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.marketplace__title h1 {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  line-height: 1.2;
}

.marketplace__subtitle {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  display: block;
}

.marketplace__actions {
  display: flex;
  gap: 8px;
}

.marketplace__btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  color: #475569;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
}

.marketplace__btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #1e293b;
}

.marketplace__btn-icon {
  font-size: 13px;
  font-weight: 600;
}

.marketplace__body {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.marketplace__iframe {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
  background: #fff;
}
</style>
