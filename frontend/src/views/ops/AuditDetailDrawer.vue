<template>
  <a-drawer
    :open="open"
    title="操作详情"
    :width="480"
    @close="$emit('update:open', false)"
  >
    <template v-if="item">
      <!-- 元信息 -->
      <div class="audit-detail__meta">
        <div class="audit-detail__meta-row">
          <span class="audit-detail__meta-label">操作人</span>
          <span class="audit-detail__meta-value">{{ item.user_name || '系统' }}</span>
        </div>
        <div class="audit-detail__meta-row">
          <span class="audit-detail__meta-label">时间</span>
          <span class="audit-detail__meta-value audit-detail__mono">{{ formatTime(item.timestamp) }}</span>
        </div>
        <div class="audit-detail__meta-row">
          <span class="audit-detail__meta-label">操作类型</span>
          <span class="audit-detail__meta-value">
            <span class="action-tag" :class="`action--${item.action}`">{{ actionLabel(item.action) }}</span>
          </span>
        </div>
        <div class="audit-detail__meta-row">
          <span class="audit-detail__meta-label">目标对象</span>
          <span class="audit-detail__meta-value">{{ item.target_name || item.target_id }}</span>
        </div>
        <div class="audit-detail__meta-row">
          <span class="audit-detail__meta-label">结果</span>
          <span class="audit-detail__meta-value">
            <span :class="item.status === 'success' ? 'status--success' : 'status--fail'">
              {{ item.status === 'success' ? '成功' : '失败' }}
            </span>
          </span>
        </div>
        <div v-if="item.details" class="audit-detail__meta-row">
          <span class="audit-detail__meta-label">详情</span>
          <span class="audit-detail__meta-value audit-detail__mono">{{ item.details }}</span>
        </div>
      </div>

      <!-- 变更对比 -->
      <div class="audit-detail__changes">
        <h3 class="audit-detail__changes-title">字段变更</h3>
        <table v-if="item.changes_json && item.changes_json.length" class="audit-detail__diff-table">
          <thead>
            <tr><th>字段</th><th>变更前</th><th>变更后</th></tr>
          </thead>
          <tbody>
            <tr v-for="(change, idx) in item.changes_json" :key="idx">
              <td class="audit-detail__diff-field">{{ change.field }}</td>
              <td class="audit-detail__diff-before">{{ formatValue(change.before) }}</td>
              <td class="audit-detail__diff-after">{{ formatValue(change.after) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="audit-detail__no-changes">此操作无字段变更记录</p>
      </div>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { Drawer as ADrawer } from 'ant-design-vue'
import type { AuditLogItem } from '../../api/governance'

defineProps<{
  open: boolean
  item: AuditLogItem | null
}>()

defineEmits<{ 'update:open': [value: boolean] }>()

const actionMap: Record<string, string> = {
  create: '创建', update: '修改', delete: '删除',
  login: '登录', export: '导出', import: '导入',
}

function actionLabel(action: string) {
  return actionMap[action] || action
}

function formatTime(ts: string) {
  return ts ? ts.replace('T', ' ').slice(0, 19) : '-'
}

function formatValue(val: unknown) {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}
</script>

<style scoped>
.audit-detail__meta {
  background: var(--neutral-50);
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.audit-detail__meta-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.audit-detail__meta-label {
  width: 72px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--neutral-500);
}
.audit-detail__meta-value {
  font-size: 13px;
  color: var(--neutral-800);
  word-break: break-all;
}
.audit-detail__mono {
  font-family: var(--font-mono);
  font-size: 12px;
}

.action-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.action--create { background: #e6fcf5; color: #10b981; }
.action--update { background: #edf2ff; color: #5c7cfa; }
.action--delete { background: #fff5f5; color: #fa5252; }
.action--login  { background: #e7f5ff; color: #339af0; }
.action--export { background: #fff9db; color: #f59f00; }
.action--import { background: #f3f0ff; color: #7950f2; }

.status--success { color: var(--status-success, #10b981); font-weight: 500; }
.status--fail { color: var(--status-error, #fa5252); font-weight: 500; }

.audit-detail__changes {
  margin-top: 24px;
}
.audit-detail__changes-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-800);
  margin-bottom: 12px;
}
.audit-detail__diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.audit-detail__diff-table th {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--neutral-200);
  color: var(--neutral-500);
  font-weight: 500;
  font-size: 12px;
}
.audit-detail__diff-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--neutral-100);
}
.audit-detail__diff-field {
  font-weight: 500;
  color: var(--neutral-700);
  width: 80px;
}
.audit-detail__diff-before {
  color: var(--status-error, #fa5252);
  text-decoration: line-through;
  opacity: 0.7;
}
.audit-detail__diff-after {
  color: var(--status-success, #10b981);
  font-weight: 500;
}
.audit-detail__no-changes {
  text-align: center;
  color: var(--neutral-400);
  font-size: 13px;
  padding: 24px 0;
}
</style>
