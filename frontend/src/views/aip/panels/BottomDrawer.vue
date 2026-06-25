<template>
  <div class="aip-bd" :style="{ height: store.bottomDrawerHeight + 'px' }">
    <div class="aip-bd__resizer" @mousedown="startResize"></div>
    <div class="aip-bd__header">
      <div class="aip-bd__tabs">
        <button class="aip-bd__tab" :class="{ active: store.bottomTab === 'logs' }" @click="store.bottomTab = 'logs'">
          执行日志 <span v-if="store.logs.length" class="aip-bd__count">{{ store.logs.length }}</span>
        </button>
        <button class="aip-bd__tab" :class="{ active: store.bottomTab === 'reasoning' }" @click="store.bottomTab = 'reasoning'">
          OAG 推理追溯 <span v-if="store.reasoning.length" class="aip-bd__count">{{ store.reasoning.length }}</span>
        </button>
        <button class="aip-bd__tab" :class="{ active: store.bottomTab === 'history' }" @click="onSwitchHistory">
          执行历史 <span v-if="store.executions.length" class="aip-bd__count">{{ store.executions.length }}</span>
        </button>
      </div>
      <div class="aip-bd__actions">
        <button class="aip-bd__btn-ghost" @click="store.clearLogs()">清空</button>
        <button class="aip-bd__btn-ghost" @click="store.bottomDrawerOpen = false">收起</button>
      </div>
    </div>

    <div class="aip-bd__body">
      <!-- 左：日志 / 推理 / 历史 -->
      <div class="aip-bd__left">
        <div v-if="store.bottomTab === 'logs'">
          <div v-if="!store.logs.length" class="aip-bd__empty">点击「▶ 执行」按钮开始执行场景</div>
          <div v-for="(l, i) in store.logs" :key="i" class="aip-bd__log" :class="`aip-bd__log--${l.level}`">
            <span class="aip-bd__log-dot"></span>
            <span class="aip-bd__log-time">{{ l.time }}</span>
            <span class="aip-bd__log-level">{{ l.level.toUpperCase() }}</span>
            <span class="aip-bd__log-msg">{{ l.message }}</span>
          </div>
        </div>

        <div v-else-if="store.bottomTab === 'reasoning'" class="aip-bd__reasoning">
          <div v-if="!store.reasoning.length" class="aip-bd__empty">执行场景后将显示 OAG 推理路径</div>
          <div v-for="(r, idx) in store.reasoning" :key="r.nodeId" class="aip-bd__reason-card" :style="{ marginLeft: (idx % 2 === 0 ? 0 : 40) + 'px' }">
            <div class="aip-bd__reason-head">
              <span class="aip-bd__reason-step">{{ idx + 1 }}</span>
              <span class="aip-bd__reason-name">{{ r.nodeName }}</span>
              <span class="aip-bd__reason-status" :class="`aip-bd__reason-status--${r.status}`">{{ r.status === 'success' ? '✓' : '✘' }} {{ r.durationMs }}ms</span>
            </div>
            <div class="aip-bd__reason-body">
              <div v-if="r.consumed.length" class="aip-bd__reason-row">
                <span class="aip-bd__reason-label">消费</span>
                <span v-for="t in r.consumed" :key="t" class="aip-tag aip-tag--blue">{{ t }}</span>
              </div>
              <div v-if="r.rules.length" class="aip-bd__reason-row">
                <span class="aip-bd__reason-label">规则</span>
                <span v-for="rl in r.rules" :key="rl" class="aip-tag aip-tag--orange">{{ rl }}</span>
              </div>
              <div v-if="r.models.length" class="aip-bd__reason-row">
                <span class="aip-bd__reason-label">模型</span>
                <span v-for="m in r.models" :key="m" class="aip-tag aip-tag--purple">{{ m }}</span>
              </div>
              <div v-if="r.writeback.length" class="aip-bd__reason-row">
                <span class="aip-bd__reason-label">写回</span>
                <span v-for="w in r.writeback" :key="w" class="aip-tag aip-tag--green">{{ w }}</span>
              </div>
              <!-- Agent ReAct Loop 轮次详情 -->
              <div v-if="r.raw && r.raw.rounds" class="aip-bd__agent-loop">
                <div class="aip-bd__agent-loop-title">Agent 推理轮次 ({{ r.raw.rounds }} 轮)</div>
                <div v-for="(round, ri) in (r.raw.agent_rounds || [])" :key="ri" class="aip-bd__agent-round">
                  <div class="aip-bd__agent-round-head">
                    <span class="aip-bd__agent-round-num">R{{ Number(ri) + 1 }}</span>
                    <span v-if="round.thought" class="aip-bd__agent-thought">{{ round.thought.slice(0, 100) }}</span>
                  </div>
                  <div v-if="round.tool_call" class="aip-bd__agent-tool">
                    <span class="aip-tag aip-tag--blue">{{ round.tool_call.name }}</span>
                    <span class="aip-bd__agent-obs">→ {{ shorten(round.observation) }}</span>
                  </div>
                </div>
              </div>
              <div class="aip-bd__reason-output">{{ r.output }}</div>
            </div>
          </div>
        </div>

        <div v-else class="aip-bd__history">
          <div v-if="!store.executions.length" class="aip-bd__empty">暂无执行记录</div>
          <div v-for="e in store.executions" :key="e.id" class="aip-bd__history-row" @click="store.viewExecution(e.id)">
            <span class="aip-bd__history-status" :class="`aip-bd__history-status--${e.status}`">{{ statusLabel(e.status) }}</span>
            <span class="aip-bd__history-time">{{ e.started_at }}</span>
            <span class="aip-bd__history-trigger">{{ e.triggered_by }}</span>
            <span class="aip-bd__history-duration">{{ e.duration_ms || 0 }}ms · {{ e.node_count }} 节点</span>
            <button class="aip-bd__btn-ghost" @click.stop="onReplay(e.id)">重放</button>
          </div>
        </div>
      </div>

      <!-- 右：节点输入/输出 -->
      <div class="aip-bd__right">
        <div class="aip-bd__right-head">
          <div class="aip-bd__sub-tabs">
            <button class="aip-bd__sub-tab" :class="{ active: store.ioTab === 'input' }" @click="store.ioTab = 'input'">输入</button>
            <button class="aip-bd__sub-tab" :class="{ active: store.ioTab === 'output' }" @click="store.ioTab = 'output'">输出</button>
          </div>
          <div class="aip-bd__view-tabs">
            <button class="aip-bd__view-tab" :class="{ active: store.ioView === 'table' }" @click="store.ioView = 'table'">Table</button>
            <button class="aip-bd__view-tab" :class="{ active: store.ioView === 'json' }" @click="store.ioView = 'json'">JSON</button>
            <button class="aip-bd__view-tab" :class="{ active: store.ioView === 'schema' }" @click="store.ioView = 'schema'">Schema</button>
          </div>
        </div>
        <div class="aip-bd__right-body">
          <div v-if="!store.selectedNode" class="aip-bd__empty">从画布选中节点查看输入/输出</div>

          <template v-else>
            <div v-if="store.ioView === 'table'">
              <table class="aip-bd__table">
                <thead><tr><th>字段</th><th>类型</th><th>值</th></tr></thead>
                <tbody>
                  <tr v-for="[k, v] in entries" :key="k">
                    <td><span class="aip-bd__cell-key">{{ k }}</span></td>
                    <td>{{ typeof v }}</td>
                    <td><span class="aip-bd__cell-val">{{ shorten(v) }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <pre v-else-if="store.ioView === 'json'" class="aip-bd__pre">{{ JSON.stringify(payload, null, 2) }}</pre>
            <div v-else class="aip-bd__schema">
              <div v-for="[k, v] in entries" :key="k" class="aip-bd__schema-row">
                <span class="aip-bd__cell-key">{{ k }}</span>
                <span class="aip-bd__cell-type">{{ typeof v }}</span>
                <span v-if="Array.isArray(v)" class="aip-tag aip-tag--gray">array · {{ v.length }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount } from 'vue'
import { useAipStore } from '../../../store/aip'
import { replayExecution } from '../../../api/aip'

const store = useAipStore()

const payload = computed(() => {
  if (!store.selectedNode) return {}
  if (store.ioTab === 'input') return { id: store.selectedNode.id, type: store.selectedNode.type, data: store.selectedNode.data }
  // 优先取真实 reasoning 中的输出
  const r = store.reasoning.find((x: any) => x.nodeId === store.selectedNode!.id)
  if (r) return { ...r, raw: r.raw }
  return { id: store.selectedNode.id, status: store.statusOf(store.selectedNode.id), message: '尚未执行' }
})
const entries = computed(() => Object.entries(payload.value || {}))

function shorten(v: any) {
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v)
  return s.length > 60 ? s.slice(0, 60) + '…' : s
}

function statusLabel(s: string) {
  return s === 'success' ? '成功' : s === 'failed' ? '失败' : s === 'running' ? '运行中' : s
}

async function onSwitchHistory() {
  store.bottomTab = 'history'
  await store.loadHistory()
}

async function onReplay(eid: string) {
  await replayExecution(eid)
  store.pushLog('info', `已发起重放: ${eid}`)
  setTimeout(() => store.loadHistory(), 1500)
}

let dragStart = 0
let dragH = 0
function startResize(e: MouseEvent) {
  dragStart = e.clientY
  dragH = store.bottomDrawerHeight
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}
function onMove(e: MouseEvent) {
  const next = dragH - (e.clientY - dragStart)
  store.bottomDrawerHeight = Math.max(120, Math.min(600, next))
}
function onUp() {
  document.removeEventListener('mousemove', onMove)
  document.removeEventListener('mouseup', onUp)
}
onBeforeUnmount(() => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) })
</script>

<style scoped>
.aip-bd {
  position: absolute; left: 0; right: 0; bottom: 0;
  background: #fff; border-top: 1px solid #e5e7eb;
  display: flex; flex-direction: column;
  z-index: 30; box-shadow: 0 -4px 12px rgba(0,0,0,.06);
}
.aip-bd__resizer { height: 4px; background: transparent; cursor: row-resize; flex-shrink: 0; }
.aip-bd__resizer:hover { background: #2E5BFF33; }
.aip-bd__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px; border-bottom: 1px solid #f0f0f0;
}
.aip-bd__tabs { display: flex; gap: 4px; }
.aip-bd__tab {
  border: none; background: transparent; padding: 6px 12px;
  font-size: 12px; cursor: pointer; color: #64748b; border-radius: 4px;
}
.aip-bd__tab:hover { background: #f8fafc; color: #1e293b; }
.aip-bd__tab.active { background: #2E5BFF; color: #fff; font-weight: 600; }
.aip-bd__count { background: #fff; color: #2E5BFF; padding: 0 5px; border-radius: 8px; font-size: 10px; margin-left: 4px; }
.aip-bd__tab:not(.active) .aip-bd__count { background: #e2e8f0; color: #475569; }
.aip-bd__btn-ghost { border: 1px solid #e2e8f0; background: #fff; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; color: #475569; margin-left: 6px; }
.aip-bd__btn-ghost:hover { background: #f8fafc; }

.aip-bd__body { flex: 1; display: flex; min-height: 0; }
.aip-bd__left { flex: 1; min-width: 0; padding: 12px 16px; overflow-y: auto; border-right: 1px solid #f0f0f0; }
.aip-bd__right { width: 40%; min-width: 320px; display: flex; flex-direction: column; }
.aip-bd__right-head { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
.aip-bd__sub-tabs, .aip-bd__view-tabs { display: flex; gap: 0; }
.aip-bd__sub-tab, .aip-bd__view-tab {
  border: 1px solid #e2e8f0; background: #fff; padding: 4px 10px; cursor: pointer;
  font-size: 11px; color: #64748b;
}
.aip-bd__sub-tab:first-child, .aip-bd__view-tab:first-child { border-radius: 4px 0 0 4px; }
.aip-bd__sub-tab:last-child, .aip-bd__view-tab:last-child { border-radius: 0 4px 4px 0; }
.aip-bd__sub-tab + .aip-bd__sub-tab, .aip-bd__view-tab + .aip-bd__view-tab { border-left: none; }
.aip-bd__sub-tab.active, .aip-bd__view-tab.active { background: #2E5BFF; color: #fff; border-color: #2E5BFF; }
.aip-bd__right-body { flex: 1; overflow: auto; padding: 12px; }

.aip-bd__empty { color: #94a3b8; text-align: center; padding: 32px 16px; font-size: 12px; }

.aip-bd__log {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 4px; font-size: 12px; line-height: 18px;
  border-bottom: 1px solid #f8fafc;
}
.aip-bd__log-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; background: #94a3b8; }
.aip-bd__log--info .aip-bd__log-dot { background: #3b82f6; }
.aip-bd__log--success .aip-bd__log-dot { background: #10b981; }
.aip-bd__log--warn .aip-bd__log-dot { background: #f59e0b; }
.aip-bd__log--error .aip-bd__log-dot { background: #ef4444; }
.aip-bd__log-time { color: #94a3b8; font-family: ui-monospace, monospace; font-size: 11px; }
.aip-bd__log-level { font-size: 10px; padding: 0 5px; border-radius: 3px; background: #f1f5f9; color: #475569; font-weight: 600; }
.aip-bd__log--success .aip-bd__log-level { background: #ecfdf5; color: #059669; }
.aip-bd__log--warn .aip-bd__log-level { background: #fef3c7; color: #b45309; }
.aip-bd__log--error .aip-bd__log-level { background: #fef2f2; color: #b91c1c; }
.aip-bd__log-msg { color: #1e293b; flex: 1; }

.aip-bd__reason-card {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
  margin-bottom: 12px; padding: 10px 12px;
  width: calc(100% - 40px);
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}
.aip-bd__reason-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.aip-bd__reason-step {
  width: 22px; height: 22px; border-radius: 50%;
  background: #2E5BFF; color: #fff; font-weight: 700; font-size: 12px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.aip-bd__reason-name { font-weight: 600; font-size: 13px; color: #1e293b; }
.aip-bd__reason-body { display: flex; flex-direction: column; gap: 6px; }
.aip-bd__reason-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.aip-bd__reason-label { font-size: 10px; color: #94a3b8; min-width: 32px; }
.aip-bd__reason-output { font-size: 12px; color: #475569; padding-top: 4px; border-top: 1px dashed #f1f5f9; margin-top: 4px; }

.aip-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.aip-tag--blue { background: #eff6ff; color: #2563eb; }
.aip-tag--orange { background: #fff7ed; color: #c2410c; }
.aip-tag--purple { background: #f5f3ff; color: #7c3aed; }
.aip-tag--green { background: #ecfdf5; color: #059669; }
.aip-tag--gray { background: #f1f5f9; color: #64748b; }

.aip-bd__table { width: 100%; border-collapse: collapse; font-size: 12px; }
.aip-bd__table th { text-align: left; padding: 6px 8px; background: #f8fafc; color: #475569; font-weight: 600; border-bottom: 1px solid #e2e8f0; }
.aip-bd__table td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
.aip-bd__cell-key { font-family: ui-monospace, monospace; color: #2563eb; font-size: 11px; }
.aip-bd__cell-val { color: #1e293b; word-break: break-all; }
.aip-bd__cell-type { color: #64748b; font-size: 10px; }

.aip-bd__pre { background: #0f172a; color: #d1d5db; padding: 12px; border-radius: 6px; font-size: 11px; line-height: 1.5; overflow: auto; max-height: 100%; }
.aip-bd__schema { display: flex; flex-direction: column; gap: 4px; }
.aip-bd__schema-row { display: flex; align-items: center; gap: 8px; padding: 5px 8px; background: #f8fafc; border-radius: 4px; font-size: 11px; }

.aip-bd__history { display: flex; flex-direction: column; gap: 4px; }
.aip-bd__history-row {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
  font-size: 12px; cursor: pointer;
}
.aip-bd__history-row:hover { background: #f8fafc; border-color: #2E5BFF; }
.aip-bd__history-status { font-size: 10px; padding: 1px 8px; border-radius: 999px; }
.aip-bd__history-status--success { background: #ecfdf5; color: #059669; }
.aip-bd__history-status--failed  { background: #fef2f2; color: #dc2626; }
.aip-bd__history-status--running { background: #eff6ff; color: #2563eb; }
.aip-bd__history-status--cancelled { background: #f1f5f9; color: #64748b; }
.aip-bd__history-time { font-family: ui-monospace, monospace; color: #1e293b; }
.aip-bd__history-trigger { color: #64748b; font-size: 11px; }
.aip-bd__history-duration { color: #94a3b8; font-size: 11px; flex: 1; }

.aip-bd__reason-status { margin-left: auto; font-size: 10px; padding: 1px 8px; border-radius: 999px; }
.aip-bd__reason-status--success { background: #ecfdf5; color: #059669; }
.aip-bd__reason-status--failed { background: #fef2f2; color: #dc2626; }

/* Agent ReAct Loop 追溯 */
.aip-bd__agent-loop { margin-top: 8px; padding-top: 8px; border-top: 1px solid #e2e8f0; }
.aip-bd__agent-loop-title { font-size: 10px; color: #64748b; font-weight: 600; margin-bottom: 6px; }
.aip-bd__agent-round { padding: 4px 8px; background: #f8fafc; border-radius: 4px; margin-bottom: 4px; border-left: 2px solid #2E5BFF; }
.aip-bd__agent-round-head { display: flex; align-items: center; gap: 6px; }
.aip-bd__agent-round-num { font-size: 10px; font-weight: 700; color: #2E5BFF; min-width: 20px; }
.aip-bd__agent-thought { font-size: 11px; color: #475569; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aip-bd__agent-tool { display: flex; align-items: center; gap: 6px; margin-top: 2px; padding-left: 26px; }
.aip-bd__agent-obs { font-size: 10px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px; }
</style>
