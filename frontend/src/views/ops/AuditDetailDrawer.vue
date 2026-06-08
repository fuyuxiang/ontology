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
          <span class="audit-detail__meta-value">
            <span class="audit-detail__user-avatar">{{ (item.user_name || '系')[0] }}</span>
            {{ item.user_name || '系统' }}
          </span>
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
            <span class="status-badge" :class="item.status === 'success' ? 'status-badge--ok' : 'status-badge--err'">
              {{ item.status === 'success' ? '✓ 成功' : '✗ 失败' }}
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
        <div v-else class="audit-detail__no-changes">
          <div class="audit-detail__no-changes-icon">📝</div>
          <p>此操作无字段变更记录</p>
        </div>
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
  padding: 18px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  border: 1px solid var(--neutral-100);
}
.audit-detail__meta-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.audit-detail__meta-label {
  width: 72px;
  flex-shrink: 0;
  font-size: 12px;
  color: var(--neutral-400);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  padding-top: 2px;
}
.audit-detail__meta-value {
  font-size: 13px;
  color: var(--neutral-800);
  word-break: break-all;
  display: flex;
  align-items: center;
  gap: 8px;
}
.audit-detail__mono {
  font-family: var(--font-mono);
  font-size: 12px;
}
.audit-detail__user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--semantic-100, #e8f0fe);
  color: var(--semantic-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}

.action-tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 600;
}
.action--create { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.action--update { background: rgba(92, 124, 250, 0.1); color: #5c7cfa; }
.action--delete { background: rgba(250, 82, 82, 0.1); color: #fa5252; }
.action--login  { background: rgba(51, 154, 240, 0.1); color: #339af0; }
.action--export { background: rgba(245, 159, 0, 0.1); color: #f59f00; }
.action--import { background: rgba(121, 80, 242, 0.1); color: #7950f2; }

.status-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.status-badge--ok { color: var(--status-success, #10b981); background: rgba(16, 185, 129, 0.08); }
.status-badge--err { color: var(--status-error, #fa5252); background: rgba(250, 82, 82, 0.08); }

.audit-detail__changes {
  margin-top: 28px;
}
.audit-detail__changes-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-800);
  margin-bottom: 14px;
}
.audit-detail__diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  border: 1px solid var(--neutral-100);
  border-radius: 8px;
  overflow: hidden;
}
.audit-detail__diff-table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--neutral-200);
  background: var(--neutral-50);
  color: var(--neutral-500);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.audit-detail__diff-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--neutral-100);
}
.audit-detail__diff-field {
  font-weight: 600;
  color: var(--neutral-700);
  width: 80px;
}
.audit-detail__diff-before {
  color: var(--status-error, #fa5252);
  text-decoration: line-through;
  opacity: 0.7;
  font-family: var(--font-mono);
  font-size: 12px;
}
.audit-detail__diff-after {
  color: var(--status-success, #10b981);
  font-weight: 600;
  font-family: var(--font-mono);
  font-size: 12px;
}
.audit-detail__no-changes {
  text-align: center;
  color: var(--neutral-400);
  font-size: 13px;
  padding: 32px 0;
}
.audit-detail__no-changes-icon {
  font-size: 32px;
  margin-bottom: 8px;
  opacity: 0.6;
}
</style>
