<template>
  <div class="ob-root ob-empty-root">
    <div class="ob-empty-blur ob-empty-blur-top"></div>
    <div class="ob-empty-blur ob-empty-blur-bottom"></div>

    <div class="ob-empty-shell">
      <div class="ob-empty-head">
        <h1>开始构建你的第一个本体</h1>
        <p>选择一种构建方式，AI 将全程辅助你完成本体设计</p>
      </div>

      <div class="ob-empty-grid">
        <button type="button" class="ob-empty-card ob-empty-card-blue" @click="emit('open-new')">
          <div class="ob-empty-visual ob-empty-visual-blue">
            <div class="ob-empty-pattern ob-empty-pattern-grid"></div>
            <div class="ob-empty-orbit ob-empty-orbit-solid"></div>
            <div class="ob-empty-orbit ob-empty-orbit-dashed"></div>
            <div class="ob-empty-glow ob-empty-glow-blue"></div>
            <div class="ob-empty-chip ob-empty-chip-top-left ob-floating-2">
              <span class="ob-empty-chip-dot"></span>
              <span>AI 分析</span>
            </div>
            <div class="ob-empty-chip ob-empty-chip-chart ob-floating-1">
              <span class="ob-empty-bar ob-empty-bar-1"></span>
              <span class="ob-empty-bar ob-empty-bar-2"></span>
              <span class="ob-empty-bar ob-empty-bar-3"></span>
            </div>
            <div class="ob-empty-chip ob-empty-chip-float ob-empty-chip-float-blue">
              <span aria-hidden="true">⇆</span>
              <span>自动匹配</span>
            </div>
            <div class="ob-empty-dot ob-empty-dot-a ob-floating-2"></div>
            <div class="ob-empty-dot ob-empty-dot-b ob-floating-1"></div>
            <div class="ob-empty-main-icon ob-empty-main-icon-blue">
              <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/>
                <path d="M6 6l4 4M18 6l-4 4M6 18l4-4M18 18l-4-4"/>
              </svg>
            </div>
          </div>
          <div class="ob-empty-card-title">场景驱动</div>
          <div class="ob-empty-card-desc">从业务场景出发，利用 AI 技术辅助提取核心本体，结合 Copilot 自动匹配已有资产。</div>
          <div class="ob-empty-card-foot">
            <span class="ob-empty-badge ob-empty-badge-blue">适合业务分析师</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
          </div>
        </button>

        <button type="button" class="ob-empty-card ob-empty-card-green" @click="emit('open-upload')">
          <div class="ob-empty-visual ob-empty-visual-green">
            <div class="ob-empty-pattern ob-empty-pattern-dot"></div>
            <div class="ob-empty-orbit ob-empty-orbit-solid"></div>
            <div class="ob-empty-orbit ob-empty-orbit-dashed"></div>
            <div class="ob-empty-glow ob-empty-glow-green"></div>
            <div class="ob-empty-chip ob-empty-chip-top-left ob-floating-1">
              <span class="ob-empty-chip-dot" style="background:#10b981"></span>
              <span>文件导入</span>
            </div>
            <div class="ob-empty-chip ob-empty-chip-left-mid ob-floating-3" aria-hidden="true">📄</div>
            <div class="ob-empty-chip ob-empty-chip-float ob-empty-chip-float-green ob-floating-2">
              <span aria-hidden="true">⏱</span>
              <span>待审核</span>
            </div>
            <div class="ob-empty-grid-line ob-empty-grid-line-top"></div>
            <div class="ob-empty-grid-line ob-empty-grid-line-bottom"></div>
            <div class="ob-empty-chip ob-empty-chip-refresh" aria-hidden="true">↻</div>
            <div class="ob-empty-main-icon ob-empty-main-icon-green">
              <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="14 3 14 9 20 9"/><path d="M9 14l3 3 5-5"/>
              </svg>
            </div>
          </div>
          <div class="ob-empty-card-title">导入驱动</div>
          <div class="ob-empty-card-desc">选择本体 JSON 文件，解析后提交审核。</div>
          <div class="ob-empty-card-foot">
            <span class="ob-empty-badge ob-empty-badge-green">适合数据工程师</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
          </div>
        </button>
      </div>
    </div>
    <slot name="modal" />
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  (e: 'open-new'): void
  (e: 'open-upload'): void
}>()
</script>
