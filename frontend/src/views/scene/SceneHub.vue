<template>
  <div class="scene-hub">
    <div class="scene-hub__header">
      <h1 class="scene-hub__title">业务场景模拟</h1>
      <p class="scene-hub__desc">选择业务场景，进入对应的智能分析与模拟工作台</p>
    </div>
    <div class="scene-hub__grid">
      <component
        v-for="item in scenes"
        :key="item.path"
        :is="item.disabled ? 'div' : 'RouterLink'"
        :to="item.disabled ? undefined : item.path"
        class="scene-card"
        :class="{ 'scene-card--disabled': item.disabled }"
      >
        <div class="scene-card__icon" :style="{ background: item.color }">
          <span v-html="item.icon"></span>
        </div>
        <div class="scene-card__body">
          <h2 class="scene-card__name">{{ item.label }}</h2>
          <p class="scene-card__desc">{{ item.description }}</p>
        </div>
        <span v-if="item.disabled" class="scene-card__tag">即将上线</span>
        <span v-else class="scene-card__tag scene-card__tag--active">已上线</span>
      </component>
    </div>
  </div>
</template>

<script setup lang="ts">
const scenes = [
  {
    path: '/scene/fttr',
    label: 'FTTR续约策划',
    description: '基于客户画像、订阅状态、流失风险模型，智能推荐续约策略，提升FTTR用户留存率',
    color: 'var(--dynamic-600, #6366f1)',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>',
    disabled: true,
  },
  {
    path: '/scene/broadband',
    label: '宽带退单原因稽核',
    description: '基于本体规则与大模型协同，自动判断退单原因合理性，提升稽核效率',
    color: 'var(--semantic-600, #0ea5e9)',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M4 3h10l4 4v14H4V3z" stroke="#fff" stroke-width="2" stroke-linejoin="round"/><path d="M14 3v4h4" stroke="#fff" stroke-width="2" stroke-linejoin="round"/><path d="M8 12h8M8 16h8" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>',
    disabled: false,
  },
  {
    path: '/scene/enterprise',
    label: '政企根因分析',
    description: '面向政企业务，以客户群体、产品服务、项目合同等为核心，支持多维下钻根因识别',
    color: 'var(--semantic-600, #0ea5e9)',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 17l4-4 3 3 4-5 4 4" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    disabled: true,
  },
  {
    path: '/scene/mnp',
    label: '携号转网预警',
    description: '基于本体实体间的流程驱动，展示携转预警从信号感知到任务分发的端到端编排',
    color: 'var(--warning-600, #f59e0b)',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 3l7 4v6l-7 4-7-4V7l7-4z" stroke="#fff" stroke-width="2" stroke-linejoin="round"/><path d="M12 7v8" stroke="#fff" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="18" r="1" fill="#fff"/></svg>',
    disabled: false,
  },
]
</script>

<style scoped>
.scene-hub {
  padding: 32px;
  max-width: 960px;
  margin: 0 auto;
}

.scene-hub__header {
  margin-bottom: 32px;
}

.scene-hub__title {
  font-size: var(--text-h1-size);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.scene-hub__desc {
  font-size: var(--text-body-size);
  color: var(--text-secondary);
  margin: 6px 0 0;
}
.scene-hub__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.scene-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  border-radius: var(--radius-lg, 12px);
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-primary, #e5e7eb);
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
  position: relative;
}

.scene-card:hover {
  border-color: var(--semantic-400, #38bdf8);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.scene-card--disabled {
  opacity: 0.55;
  cursor: not-allowed;
  pointer-events: none;
}

.scene-card__icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md, 8px);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.scene-card__body {
  flex: 1;
  min-width: 0;
}

.scene-card__name {
  font-size: var(--text-h3-size);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.scene-card__desc {
  font-size: var(--text-body-size);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.scene-card__tag {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: var(--text-caption-size);
  padding: 2px 8px;
  border-radius: var(--radius-full, 999px);
  background: var(--bg-secondary, #f3f4f6);
  color: var(--text-tertiary, #9ca3af);
  font-weight: 500;
}

.scene-card__tag--active {
  background: var(--success-100, #dcfce7);
  color: var(--success-700, #15803d);
}
</style>
