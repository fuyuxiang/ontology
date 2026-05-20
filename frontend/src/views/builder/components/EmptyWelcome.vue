<template>
  <div class="ob-empty-shell">
    <div class="ob-empty-decor ob-empty-decor--blue"></div>
    <div class="ob-empty-decor ob-empty-decor--purple"></div>
    <div class="ob-empty-decor ob-empty-decor--green"></div>
    <div class="ob-empty-grid"></div>

    <div class="ob-empty-inner">
      <div class="ob-empty-header">
        <div class="ob-empty-eyebrow">AI 场景驱动 · 资产嗅探 · 本体初始化 · 走测审批 · 一键发布</div>
        <h1 class="ob-empty-title">本体构建器 · AI Builder</h1>
        <p class="ob-empty-sub">开始构建你的第一个本体 — 选择一种构建方式，AI 将全程辅助你完成本体设计</p>
      </div>

      <div class="ob-empty-cards">
        <div class="ob-empty-card ob-empty-card--blue" @click="$emit('open-new')">
          <div class="ob-empty-card__icon">AI</div>
          <div class="ob-empty-card__tag">适合业务分析师</div>
          <div class="ob-empty-card__title">场景驱动</div>
          <div class="ob-empty-card__desc">从业务场景出发，利用 AI 技术辅助提取核心本体，结合 Copilot 自动匹配已有资产。</div>
          <div class="ob-empty-card__cta">开始 AI 构建 →</div>
        </div>

        <div class="ob-empty-card ob-empty-card--green" @click="$emit('open-upload')">
          <div class="ob-empty-card__icon">UP</div>
          <div class="ob-empty-card__tag">适合数据工程师</div>
          <div class="ob-empty-card__title">导入驱动</div>
          <div class="ob-empty-card__desc">上传已构建好的 OWL / JSON 本体文件，系统解析对象、属性与关系后进入导入审核流程。</div>
          <div class="ob-empty-card__cta">上传本体文件 →</div>
        </div>
      </div>

      <div class="ob-empty-tips">
        <span class="ob-empty-chip"><i class="dot"></i>场景识别</span>
        <span class="ob-empty-chip"><i class="dot"></i>资产嗅探</span>
        <span class="ob-empty-chip"><i class="dot"></i>本体初始化</span>
        <span class="ob-empty-chip"><i class="dot"></i>专家走测</span>
        <span class="ob-empty-chip"><i class="dot"></i>水合演练</span>
        <span class="ob-empty-chip"><i class="dot"></i>一键发布</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{
  (e: 'open-new'): void
  (e: 'open-upload'): void
}>()
</script>

<style scoped>
.ob-empty-shell {
  position: relative;
  min-height: calc(100vh - 120px);
  padding: 56px 48px;
  overflow: hidden;
  background:
    radial-gradient(1200px 600px at 0% 0%, rgba(99, 102, 241, 0.08), transparent 60%),
    radial-gradient(1200px 600px at 100% 100%, rgba(139, 92, 246, 0.08), transparent 60%),
    #f8fafc;
}
.ob-empty-decor {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  pointer-events: none;
}
.ob-empty-decor--blue { width: 320px; height: 320px; top: -80px; left: 10%; background: #6366f1; }
.ob-empty-decor--purple { width: 280px; height: 280px; bottom: 10%; right: 10%; background: #8b5cf6; }
.ob-empty-decor--green { width: 240px; height: 240px; top: 30%; right: 20%; background: #10b981; opacity: 0.25; }
.ob-empty-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(99,102,241,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,102,241,0.04) 1px, transparent 1px);
  background-size: 36px 36px;
  pointer-events: none;
}
.ob-empty-inner { position: relative; max-width: 1080px; margin: 0 auto; }
.ob-empty-header { text-align: center; margin-bottom: 56px; }
.ob-empty-eyebrow {
  display: inline-block; padding: 6px 16px; border-radius: 999px;
  background: rgba(99, 102, 241, 0.12); color: #4f46e5;
  font-size: 12px; font-weight: 500; letter-spacing: 0.4px;
  margin-bottom: 18px;
}
.ob-empty-title {
  font-size: 36px; font-weight: 700; color: #1e293b;
  letter-spacing: -1px; margin: 0 0 16px;
  background: linear-gradient(135deg, #1e293b 0%, #4f46e5 60%, #8b5cf6 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.ob-empty-sub { font-size: 15px; color: #64748b; line-height: 1.7; }

.ob-empty-cards {
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 40px;
}
.ob-empty-card {
  position: relative;
  padding: 32px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 200ms ease-out;
  overflow: hidden;
}
.ob-empty-card::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(135deg, transparent 0%, rgba(99,102,241,0.06) 100%);
  opacity: 0; transition: opacity 200ms ease-out;
}
.ob-empty-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 24px 40px -12px rgba(15, 23, 42, 0.15);
  border-color: transparent;
}
.ob-empty-card:hover::before { opacity: 1; }
.ob-empty-card--blue:hover { border-color: rgba(99, 102, 241, 0.3); }
.ob-empty-card--green:hover { border-color: rgba(16, 185, 129, 0.3); }
.ob-empty-card__icon {
  width: 64px; height: 64px; border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 700; color: #fff;
  letter-spacing: 0.5px;
  margin-bottom: 20px;
  position: relative;
  box-shadow: 0 8px 16px -4px rgba(0,0,0,0.15);
}
.ob-empty-card--blue .ob-empty-card__icon {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
}
.ob-empty-card--green .ob-empty-card__icon {
  background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
}
.ob-empty-card__tag {
  display: inline-block; padding: 4px 10px; border-radius: 6px;
  background: #f1f5f9; color: #64748b;
  font-size: 11px; font-weight: 500;
  margin-bottom: 12px;
  position: relative;
}
.ob-empty-card__title {
  font-size: 22px; font-weight: 700; color: #0f172a;
  margin-bottom: 12px; position: relative;
}
.ob-empty-card__desc {
  font-size: 13px; line-height: 1.7; color: #64748b;
  margin-bottom: 20px; position: relative;
}
.ob-empty-card__cta {
  font-size: 13px; font-weight: 600; color: #4f46e5;
  position: relative;
}
.ob-empty-card--green .ob-empty-card__cta { color: #0d9488; }

.ob-empty-tips {
  display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
}
.ob-empty-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: 999px;
  background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(8px);
  border: 1px solid #e2e8f0;
  font-size: 12px; color: #475569;
}
.ob-empty-chip .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}
</style>
