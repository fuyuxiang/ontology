<template>
  <a-drawer
    :open="store.sceneDrawerOpen"
    @close="store.sceneDrawerOpen = false"
    placement="right"
    :width="480"
    :body-style="{ padding: 0 }"
    :header-style="{ display: 'none' }"
  >
    <div class="aip-sd">
      <div class="aip-sd__header">
        <div class="aip-sd__title-wrap">
          <div class="aip-sd__title">场景配置</div>
          <div class="aip-sd__sub">{{ scene?.name || '—' }}</div>
        </div>
        <button class="aip-sd__close" @click="store.sceneDrawerOpen = false">×</button>
      </div>

      <div class="aip-sd__tabs">
        <button class="aip-sd__tab" :class="{ active: store.sceneDrawerTab === 'basic' }" @click="store.sceneDrawerTab = 'basic'">基本信息</button>
        <button class="aip-sd__tab" :class="{ active: store.sceneDrawerTab === 'trigger' }" @click="store.sceneDrawerTab = 'trigger'">触发配置</button>
        <button class="aip-sd__tab" :class="{ active: store.sceneDrawerTab === 'history' }" @click="store.sceneDrawerTab = 'history'">执行历史</button>
      </div>

      <div class="aip-sd__body" v-if="scene">
        <!-- 基本信息 -->
        <div v-if="store.sceneDrawerTab === 'basic'">
          <div class="aip-field"><label>场景 ID</label><input class="aip-input" :value="scene.id" disabled /></div>
          <div class="aip-field"><label>场景名称</label><input class="aip-input" v-model="scene.name" @input="store.markDirty()" /></div>
          <div class="aip-field"><label>所属分组</label><input class="aip-input" v-model="scene.group_name" @input="store.markDirty()" /></div>
          <div class="aip-field"><label>状态</label>
            <div class="aip-status-row">
              <span class="aip-status-pill" :class="`aip-status-pill--${scene.status}`">{{ scene.status === 'published' ? '已发布' : '草稿' }}</span>
              <span class="aip-status-pill aip-status-pill--draft" v-if="scene.version">v{{ scene.version }}</span>
            </div>
          </div>
          <div class="aip-field"><label>描述</label><textarea class="aip-input aip-input--ta" rows="6" v-model="scene.description" @input="store.markDirty()"></textarea></div>
          <div class="aip-field">
            <label>关联本体（{{ (scene.ontology_bindings || []).length }}）</label>
            <div class="aip-tag-row">
              <span v-for="o in (scene.ontology_bindings || [])" :key="o" class="aip-tag aip-tag--blue">{{ o }}</span>
            </div>
          </div>
          <div class="aip-field"><label>统计数据</label>
            <div class="aip-stats">
              <div v-for="(v, k) in (scene.stats || {})" :key="k" class="aip-stat">
                <div class="aip-stat__val">{{ v }}</div>
                <div class="aip-stat__label">{{ k }}</div>
              </div>
            </div>
          </div>
          <div class="aip-field aip-field--row">
            <span class="aip-field__inline-label">创建时间</span>
            <span>{{ scene.created_at }}</span>
          </div>
          <div class="aip-field aip-field--row">
            <span class="aip-field__inline-label">更新时间</span>
            <span>{{ scene.updated_at }}</span>
          </div>
        </div>

        <!-- 触发配置 -->
        <div v-else-if="store.sceneDrawerTab === 'trigger'">
          <div class="aip-field">
            <label>触发类型</label>
            <div class="aip-trigger-types">
              <button v-for="t in TRIGGERS" :key="t.value"
                class="aip-trigger-card" :class="{ active: triggerForm.type === t.value }"
                @click="triggerForm.type = t.value as any">
                <span class="aip-trigger-card__icon" v-html="t.icon"></span>
                <span class="aip-trigger-card__label">{{ t.label }}</span>
                <span class="aip-trigger-card__desc">{{ t.desc }}</span>
              </button>
            </div>
          </div>
          <div class="aip-field">
            <label>启用状态</label>
            <label class="aip-switch">
              <input type="checkbox" v-model="triggerForm.enabled" />
              <span>{{ triggerForm.enabled ? '已启用' : '已暂停' }}</span>
            </label>
          </div>

          <template v-if="triggerForm.type === 'schedule'">
            <div class="aip-field">
              <label>频率</label>
              <select class="aip-input" v-model="triggerForm.frequency" @change="updateCron">
                <option value="daily">每天</option>
                <option value="weekly">每周一</option>
                <option value="monthly">每月 1 号</option>
                <option value="custom">自定义 Cron</option>
              </select>
            </div>
            <div class="aip-field aip-field--row" v-if="triggerForm.frequency !== 'custom'">
              <span class="aip-field__inline-label">执行时间</span>
              <input type="number" class="aip-input aip-input--xs" min="0" max="23" v-model.number="triggerForm.hour" @input="updateCron" />
              <span>:</span>
              <input type="number" class="aip-input aip-input--xs" min="0" max="59" v-model.number="triggerForm.minute" @input="updateCron" />
              <span class="aip-field__hint">{{ triggerForm.timezone }}</span>
            </div>
            <div class="aip-field">
              <label>Cron 表达式（5 字段，UTC/{{ triggerForm.timezone }}）</label>
              <input class="aip-input" v-model="triggerForm.cron_expr" placeholder="0 8 * * *" />
            </div>

            <div class="aip-cron-preset">
              <span class="aip-cron-preset__label">快速选择</span>
              <button v-for="p in CRON_PRESETS" :key="p.label" class="aip-cron-chip" @click="applyPreset(p)">{{ p.label }}</button>
            </div>
          </template>

          <template v-else-if="triggerForm.type === 'event'">
            <div class="aip-field"><label>监听本体</label>
              <select class="aip-input" v-model="triggerForm.event_entity">
                <option value="">不限</option>
                <option v-for="o in (scene.ontology_bindings || [])" :key="o" :value="o">{{ o }}</option>
              </select>
            </div>
            <div class="aip-field"><label>事件类型</label>
              <select class="aip-input" v-model="triggerForm.event_action">
                <option value="">所有</option>
                <option value="created">created</option>
                <option value="updated">updated</option>
                <option value="deleted">deleted</option>
              </select>
            </div>
          </template>

          <template v-else-if="triggerForm.type === 'webhook'">
            <div class="aip-field"><label>Webhook URL</label>
              <input class="aip-input" :value="webhookUrl" disabled />
            </div>
            <div class="aip-field"><label>Secret</label>
              <input class="aip-input" v-model="triggerForm.webhook_secret" placeholder="可选 — 用于 HMAC SHA256 签名校验" />
            </div>
            <div class="aip-field__hint">
              触发方式：POST {{ webhookUrl }}<br />
              Header: <code>X-AIP-Signature: sha256=&lt;hex&gt;</code>（若配置了 secret）
            </div>
          </template>

          <template v-else>
            <div class="aip-field">
              <div class="aip-field__hint">手动触发：仅可通过页面顶部的「▶ 执行」按钮启动</div>
            </div>
          </template>

          <div class="aip-field aip-field--row" style="margin-top: 12px;">
            <button class="aip-btn aip-btn--primary" @click="onSaveTrigger">保存触发器</button>
            <button class="aip-btn aip-btn--ghost" @click="onTestFire" :disabled="!triggerForm.enabled">立即测试触发</button>
            <span class="aip-field__hint" v-if="lastFiredAt">上次触发: {{ lastFiredAt }} · 累计 {{ fireCount }} 次</span>
          </div>
        </div>

        <!-- 执行历史 -->
        <div v-else>
          <div v-if="!history.length" class="aip-bd__empty">暂无执行记录</div>
          <div v-for="h in history" :key="h.id" class="aip-history">
            <div class="aip-history__row">
              <span class="aip-history__status" :class="`aip-history__status--${h.status}`">
                {{ h.status === 'success' ? '成功' : h.status === 'failed' ? '失败' : '运行中' }}
              </span>
              <span class="aip-history__time">{{ h.started_at }}</span>
              <span class="aip-history__trigger">{{ h.triggered_by }}</span>
            </div>
            <div class="aip-history__meta">
              <span>{{ h.duration_ms || 0 }}ms</span>
              <span>·</span>
              <span>{{ h.node_count }} 个节点</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useAipStore } from '../../../store/aip'

const store = useAipStore()
const scene = computed(() => store.currentScene)
const history = computed(() => store.executions)

const TRIGGERS = [
  { value: 'schedule', label: '定时触发', desc: 'Cron / 每日 / 每周 / 每月', icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 4v4l3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' },
  { value: 'event', label: '事件触发', desc: '本体对象 CRUD 事件', icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M8 1l1.5 4.5H14l-3.7 2.7L11.8 13 8 10.3 4.2 13l1.5-4.8L2 5.5h4.5L8 1z" stroke="currentColor" stroke-width="1.3"/></svg>' },
  { value: 'webhook', label: 'Webhook', desc: 'HTTP POST 触发', icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M5 11a3 3 0 100-6 3 3 0 000 6z" stroke="currentColor" stroke-width="1.5"/><path d="M11 7l-3 4M5 11l-3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' },
  { value: 'manual', label: '手动触发', desc: '页面顶部点击执行', icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M5 3l9 5-9 5V3z" fill="currentColor"/></svg>' },
] as const

const CRON_PRESETS = [
  { label: '每天 08:00', frequency: 'daily' as const, hour: 8, minute: 0 },
  { label: '每天 09:00', frequency: 'daily' as const, hour: 9, minute: 0 },
  { label: '每周一 09:00', frequency: 'weekly' as const, hour: 9, minute: 0 },
  { label: '每月 1 号 09:00', frequency: 'monthly' as const, hour: 9, minute: 0 },
  { label: '每小时整点', frequency: 'custom' as const, hour: 0, minute: 0, cron: '0 * * * *' },
]

interface TriggerForm {
  type: 'schedule' | 'event' | 'webhook' | 'manual'
  enabled: boolean
  frequency: 'daily' | 'weekly' | 'monthly' | 'custom'
  hour: number
  minute: number
  cron_expr: string
  timezone: string
  event_entity: string
  event_action: string
  webhook_secret: string
  webhook_path: string
}

const triggerForm = ref<TriggerForm>({
  type: 'manual',
  enabled: false,
  frequency: 'daily',
  hour: 9, minute: 0,
  cron_expr: '',
  timezone: 'Asia/Shanghai',
  event_entity: '',
  event_action: '',
  webhook_secret: '',
  webhook_path: '',
})

const lastFiredAt = computed(() => store.trigger?.last_fired_at || '')
const fireCount = computed(() => store.trigger?.fire_count || 0)
const webhookUrl = computed(() => {
  const path = triggerForm.value.webhook_path || store.trigger?.webhook_path || '<待保存后生成>'
  return `${window.location.origin}/api/v1/aip/webhooks/${path}`
})

function syncFormFromStore() {
  const t = store.trigger
  if (!t) return
  triggerForm.value = {
    type: (t.type as any) || 'manual',
    enabled: !!t.enabled,
    frequency: ((t.schedule_payload || {}).frequency as any) || 'daily',
    hour: ((t.schedule_payload || {}).hour as any) ?? 9,
    minute: ((t.schedule_payload || {}).minute as any) ?? 0,
    cron_expr: t.cron_expr || '',
    timezone: t.timezone || 'Asia/Shanghai',
    event_entity: t.event_entity || '',
    event_action: t.event_action || '',
    webhook_secret: t.webhook_secret || '',
    webhook_path: t.webhook_path || '',
  }
}

watch(() => store.currentSceneId, () => syncFormFromStore())
watch(() => store.trigger, () => syncFormFromStore(), { deep: true })
onMounted(syncFormFromStore)

function updateCron() {
  const f = triggerForm.value
  const h = Math.max(0, Math.min(23, Number(f.hour) || 0))
  const m = Math.max(0, Math.min(59, Number(f.minute) || 0))
  if (f.frequency === 'daily') f.cron_expr = `${m} ${h} * * *`
  else if (f.frequency === 'weekly') f.cron_expr = `${m} ${h} * * 1`
  else if (f.frequency === 'monthly') f.cron_expr = `${m} ${h} 1 * *`
}

function applyPreset(p: any) {
  triggerForm.value.frequency = p.frequency
  triggerForm.value.hour = p.hour
  triggerForm.value.minute = p.minute
  if (p.cron) triggerForm.value.cron_expr = p.cron
  else updateCron()
}

async function onSaveTrigger() {
  const f = triggerForm.value
  await store.saveTrigger({
    type: f.type,
    enabled: f.enabled,
    cron_expr: f.cron_expr,
    timezone: f.timezone,
    schedule_payload: {
      frequency: f.frequency, hour: f.hour, minute: f.minute, timezone: f.timezone,
    },
    event_entity: f.event_entity || undefined,
    event_action: f.event_action || undefined,
    webhook_secret: f.webhook_secret || undefined,
  })
  store.pushLog('success', '触发器已保存')
}

async function onTestFire() {
  await store.fireTriggerOnce()
}
</script>

<style scoped>
.aip-sd { display: flex; flex-direction: column; height: 100%; background: #fff; }
.aip-sd__header {
  display: flex; align-items: center; padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}
.aip-sd__title-wrap { flex: 1; min-width: 0; }
.aip-sd__title { font-size: 16px; font-weight: 700; color: #1e293b; }
.aip-sd__sub { font-size: 11px; color: #64748b; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aip-sd__close {
  width: 28px; height: 28px; border: none; background: transparent;
  font-size: 18px; color: #94a3b8; cursor: pointer; border-radius: 4px;
}
.aip-sd__close:hover { background: #f1f5f9; color: #1e293b; }

.aip-sd__tabs { display: flex; padding: 0 20px; border-bottom: 1px solid #f0f0f0; gap: 4px; }
.aip-sd__tab {
  border: none; background: transparent; padding: 10px 14px;
  font-size: 12px; cursor: pointer; color: #64748b; border-bottom: 2px solid transparent;
}
.aip-sd__tab:hover { color: #1e293b; }
.aip-sd__tab.active { color: #2E5BFF; border-bottom-color: #2E5BFF; font-weight: 600; }

.aip-sd__body { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; }

.aip-field { display: flex; flex-direction: column; gap: 4px; }
.aip-field--row { flex-direction: row; align-items: center; gap: 8px; font-size: 12px; color: #475569; }
.aip-field__inline-label { color: #94a3b8; min-width: 64px; font-size: 11px; }
.aip-field > label { font-size: 11px; color: #475569; font-weight: 500; }
.aip-field__hint { font-size: 11px; color: #94a3b8; }
.aip-input {
  width: 100%; padding: 6px 10px; border: 1px solid #e2e8f0;
  border-radius: 4px; font-size: 12px; color: #1e293b; outline: none; background: #fff;
}
.aip-input:focus { border-color: #2E5BFF; box-shadow: 0 0 0 2px rgba(46,91,255,.15); }
.aip-input--ta { resize: vertical; min-height: 60px; }
.aip-input--xs { width: 60px; padding: 4px 6px; text-align: center; }

.aip-status-pill { font-size: 10px; padding: 2px 8px; border-radius: 999px; }
.aip-status-pill--published { background: #ecfdf5; color: #10b981; }
.aip-status-pill--draft { background: #fffbeb; color: #f59e0b; }

.aip-tag-row { display: flex; flex-wrap: wrap; gap: 4px; }
.aip-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.aip-tag--blue { background: #eff6ff; color: #2563eb; }

.aip-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.aip-stat { background: #f8fafc; padding: 10px; border-radius: 6px; text-align: center; border: 1px solid #f1f5f9; }
.aip-stat__val { font-size: 18px; font-weight: 700; color: #2E5BFF; }
.aip-stat__label { font-size: 10px; color: #64748b; margin-top: 2px; }

.aip-trigger-types { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.aip-trigger-card {
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px;
  background: #fff; border: 1.5px solid #e2e8f0; border-radius: 6px;
  padding: 10px 12px; cursor: pointer; text-align: left;
  color: #475569;
}
.aip-trigger-card:hover { border-color: #cbd5e1; }
.aip-trigger-card.active { border-color: #2E5BFF; background: rgba(46,91,255,.04); color: #2E5BFF; }
.aip-trigger-card__icon { color: inherit; }
.aip-trigger-card__label { font-size: 12px; font-weight: 600; }
.aip-trigger-card__desc { font-size: 10px; color: #94a3b8; }
.aip-trigger-card.active .aip-trigger-card__desc { color: #2E5BFF; }

.aip-switch { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: #475569; cursor: pointer; }
.aip-switch input { width: 36px; height: 20px; appearance: none; background: #cbd5e1; border-radius: 999px; position: relative; cursor: pointer; outline: none; }
.aip-switch input::after { content: ''; width: 16px; height: 16px; background: #fff; border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: left .2s; }
.aip-switch input:checked { background: #2E5BFF; }
.aip-switch input:checked::after { left: 18px; }

.aip-cron-preset { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; padding-top: 8px; }
.aip-cron-preset__label { font-size: 10px; color: #94a3b8; }
.aip-cron-chip { border: 1px solid #e2e8f0; background: #fff; padding: 3px 8px; border-radius: 999px; font-size: 11px; cursor: pointer; color: #475569; }
.aip-cron-chip:hover { border-color: #2E5BFF; color: #2E5BFF; }

.aip-history { padding: 10px 12px; background: #f8fafc; border-radius: 6px; margin-bottom: 8px; }
.aip-history__row { display: flex; align-items: center; gap: 10px; }
.aip-history__status { font-size: 10px; padding: 1px 8px; border-radius: 4px; font-weight: 600; }
.aip-history__status--success { background: #ecfdf5; color: #059669; }
.aip-history__status--error { background: #fef2f2; color: #dc2626; }
.aip-history__status--running { background: #eff6ff; color: #2563eb; }
.aip-history__time { font-size: 12px; color: #1e293b; font-family: ui-monospace, monospace; }
.aip-history__trigger { font-size: 11px; color: #64748b; margin-left: auto; }
.aip-history__meta { font-size: 11px; color: #94a3b8; padding-top: 4px; display: flex; gap: 6px; }

.aip-bd__empty { color: #94a3b8; text-align: center; padding: 32px 16px; font-size: 12px; }
</style>
