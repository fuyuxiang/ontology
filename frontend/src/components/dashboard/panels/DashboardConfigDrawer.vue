<template>
  <Transition name="drawer-slide">
    <div v-if="visible" class="dc-drawer">
      <div class="dc-drawer__mask" @click="$emit('close')" />
      <div class="dc-drawer__panel">
        <div class="dc-drawer__header">
          <span class="dc-drawer__title">仪表盘配置</span>
          <button class="dc-drawer__close" @click="$emit('close')">✕</button>
        </div>

        <div class="dc-drawer__body">
          <div class="dc-section">
            <div class="dc-section__label">自动刷新间隔（秒）</div>
            <input v-model.number="localConfig.refresh_interval" type="number" min="10" max="3600" class="dc-input" />
          </div>

          <div class="dc-section">
            <div class="dc-section__label">视图操作</div>
            <button class="dc-btn dc-btn--full" @click="$emit('reset-view')">重置视角</button>
          </div>

          <div class="dc-section__label" style="margin-bottom:8px">卡片配置</div>
          <div v-for="(card, i) in localConfig.cards_config" :key="card.key" class="dc-card">
            <div class="dc-card__header">
              <label class="dc-toggle">
                <input type="checkbox" v-model="card.enabled" />
                <span class="dc-toggle__track"></span>
              </label>
              <input v-model="card.title" class="dc-input dc-input--title" :disabled="!card.enabled" />
            </div>
            <div v-if="card.enabled" class="dc-card__items">
              <div v-for="(item, j) in card.items" :key="j" class="dc-item">
                <span class="dc-item__type">{{ itemTypeLabel(item) }}</span>
                <input v-if="item.type === 'static'" v-model="item.text" class="dc-input dc-input--sm" placeholder="显示文字" />
                <input v-if="item.type === 'dynamic'" v-model="item.label" class="dc-input dc-input--sm" placeholder="单位后缀" />
                <input v-if="item.type === 'top_rules' || item.type === 'datasources' || item.type === 'recent_activities'"
                  v-model.number="item.count" type="number" min="1" max="10" class="dc-input dc-input--sm dc-input--num" placeholder="条数" />
                <button class="dc-item__del" @click="card.items.splice(j, 1)">×</button>
              </div>
              <button class="dc-add-item" @click="addItem(card)">+ 添加项</button>
            </div>
          </div>
        </div>

        <div class="dc-drawer__footer">
          <button class="dc-btn dc-btn--ghost" @click="$emit('close')">取消</button>
          <button class="dc-btn dc-btn--primary" :disabled="saving" @click="handleSave">
            {{ saving ? '保存中...' : '保存配置' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { dashboardApi } from '../../../api/dashboard'
import type { DashboardConfig, CardConfig, CardItemConfig } from '../../../api/dashboard'

const props = defineProps<{ visible: boolean; config: DashboardConfig }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', cfg: DashboardConfig): void
  (e: 'reset-view'): void
}>()

const saving = ref(false)
const localConfig = ref<DashboardConfig>(JSON.parse(JSON.stringify(props.config)))

watch(() => props.config, (v) => {
  localConfig.value = JSON.parse(JSON.stringify(v))
}, { deep: true })

function itemTypeLabel(item: CardItemConfig) {
  const map: Record<string, string> = {
    dynamic: '动态', static: '静态', top_rules: '规则TOP', datasources: '数据源',
    rule_priority: '规则优先级', recent_activities: '近期活动',
  }
  return map[item.type] || item.type
}

function addItem(card: CardConfig) {
  card.items.push({ type: 'static', text: '新项目' })
}

async function handleSave() {
  saving.value = true
  try {
    await dashboardApi.saveConfig(localConfig.value)
    emit('saved', localConfig.value)
    emit('close')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.dc-drawer { position: fixed; inset: 0; z-index: 500; }
.dc-drawer__mask { position: absolute; inset: 0; background: rgba(0,0,0,.3); }
.dc-drawer__panel {
  position: absolute; right: 0; top: 0; bottom: 0; width: 380px;
  background: var(--color-bg, #fff); border-left: 1px solid var(--color-border, #e2e8f0);
  display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(0,0,0,.1);
}
.dc-drawer__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--color-border, #e2e8f0); flex-shrink: 0;
}
.dc-drawer__title { font-size: var(--text-body-size); font-weight: 700; color: var(--color-text, #0f172a); }
.dc-drawer__close { background: none; border: none; cursor: pointer; font-size: var(--text-body-size); color: var(--color-text-3, #64748b); padding: 2px 6px; border-radius: 4px; }
.dc-drawer__close:hover { background: var(--color-bg-2, #f1f5f9); }
.dc-drawer__body { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 16px; }
.dc-drawer__footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 20px; border-top: 1px solid var(--color-border, #e2e8f0); flex-shrink: 0;
}
.dc-section { display: flex; flex-direction: column; gap: 6px; }
.dc-section__label { font-size: var(--text-caption-size); font-weight: 600; color: var(--color-text-3, #64748b); text-transform: uppercase; letter-spacing: .05em; }
.dc-input {
  padding: 6px 9px; border-radius: 6px; font-size: var(--text-code-size);
  border: 1px solid var(--color-border, #e2e8f0); background: var(--color-bg, #fff);
  color: var(--color-text, #0f172a); outline: none; width: 100%; box-sizing: border-box;
}
.dc-input:focus { border-color: var(--semantic-600); }
.dc-input--title { font-weight: 600; }
.dc-input--sm { width: auto; flex: 1; min-width: 0; }
.dc-input--num { width: 60px; flex: none; }
.dc-card {
  border: 1px solid var(--color-border, #e2e8f0); border-radius: 8px; overflow: hidden;
}
.dc-card__header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--color-bg-2, #f8fafc); }
.dc-card__items { padding: 8px 12px; display: flex; flex-direction: column; gap: 6px; }
.dc-item { display: flex; align-items: center; gap: 6px; }
.dc-item__type { font-size: var(--text-caption-upper-size); font-weight: 600; color: var(--semantic-600); background: var(--tier2-bg); padding: 2px 6px; border-radius: 4px; white-space: nowrap; flex-shrink: 0; }
.dc-item__del { background: none; border: none; cursor: pointer; color: var(--neutral-500); font-size: var(--text-h3-size); line-height: 1; padding: 0 2px; flex-shrink: 0; }
.dc-item__del:hover { color: var(--status-error); }
.dc-add-item { font-size: var(--text-caption-size); color: var(--semantic-600); background: none; border: 1px dashed #c4b5fd; border-radius: 5px; padding: 4px 10px; cursor: pointer; width: 100%; }
.dc-add-item:hover { background: var(--tier2-bg); }
.dc-toggle { display: flex; align-items: center; cursor: pointer; flex-shrink: 0; }
.dc-toggle input { display: none; }
.dc-toggle__track {
  width: 32px; height: 18px; border-radius: 9px; background: var(--neutral-400);
  position: relative; transition: background .15s;
}
.dc-toggle__track::after {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 14px; height: 14px; border-radius: 50%; background: var(--neutral-0);
  transition: transform .15s;
}
.dc-toggle input:checked + .dc-toggle__track { background: var(--semantic-600); }
.dc-toggle input:checked + .dc-toggle__track::after { transform: translateX(14px); }
.dc-btn {
  padding: 6px 14px; border-radius: 6px; font-size: var(--text-code-size); font-weight: 500;
  cursor: pointer; border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-bg, #fff); color: var(--color-text, #0f172a); transition: all .15s;
}
.dc-btn--primary { background: var(--semantic-600); border-color: var(--semantic-600); color: var(--neutral-0); }
.dc-btn--primary:hover:not(:disabled) { background: var(--semantic-800); }
.dc-btn--primary:disabled { opacity: .5; cursor: not-allowed; }
.dc-btn--ghost { color: var(--color-text-3, #64748b); }
.dc-btn--ghost:hover { background: var(--color-bg-2, #f1f5f9); }
.dc-btn--full { width: 100%; color: var(--semantic-700); border-color: rgba(76, 110, 245, 0.28); background: rgba(76, 110, 245, 0.06); }
.dc-btn--full:hover { background: rgba(76, 110, 245, 0.12); border-color: rgba(76, 110, 245, 0.42); }
.drawer-slide-enter-active, .drawer-slide-leave-active { transition: all .2s ease; }
.drawer-slide-enter-from .dc-drawer__panel, .drawer-slide-leave-to .dc-drawer__panel { transform: translateX(100%); }
.drawer-slide-enter-from .dc-drawer__mask, .drawer-slide-leave-to .dc-drawer__mask { opacity: 0; }
</style>
