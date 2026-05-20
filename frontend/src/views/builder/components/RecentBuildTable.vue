<template>
  <div class="ob-recent">
    <div class="ob-recent__header">
      <div>
        <div class="ob-recent__eyebrow">本体构建器 · AI Builder</div>
        <h2 class="ob-recent__title">最近构建</h2>
        <p class="ob-recent__sub">AI场景驱动 · 资产嗅探 · 本体初始化 · 走测审批 · 一键发布</p>
      </div>
      <button class="ob-recent-new-btn" @click="$emit('new')">
        <span class="plus">+</span> 新建本体
      </button>
    </div>

    <div class="ob-recent-table">
      <div class="ob-recent-row ob-recent-row--head">
        <div>任务名称</div>
        <div>所属场景</div>
        <div>构建方式</div>
        <div>当前阶段</div>
        <div>审核状态</div>
        <div>创建人</div>
        <div>更新时间</div>
        <div class="actions">操作</div>
      </div>

      <div
        v-for="s in sortedSessions"
        :key="s.sessionId"
        class="ob-recent-row"
      >
        <div class="cell--name">
          <div class="name">{{ s.ontologyName }}</div>
          <div class="meta">{{ s.ontologyClasses.length }} 对象 · {{ s.ontologyRelations.length }} 关系</div>
        </div>
        <div class="cell--scene">{{ s.scenarioName }}</div>
        <div>
          <span class="ob-tag" :class="`ob-tag--${s.buildMethod}`">
            {{ s.buildMethod === 'ai' ? 'AI 构建' : '导入构建' }}
          </span>
        </div>
        <div>
          <span class="ob-tag" :class="`ob-tag--${stageTone(s.status)}`">{{ stageLabel(s.status) }}</span>
        </div>
        <div>
          <span class="ob-tag" :class="`ob-tag--${reviewTone(s.status)}`">{{ reviewLabel(s.status) }}</span>
        </div>
        <div>{{ s.createdBy }}</div>
        <div>{{ formatTime(s.updatedAt) }}</div>
        <div class="actions">
          <a-button
            v-if="s.status === 'published'"
            type="link" size="small"
            @click="$emit('view', s)"
          >查看</a-button>
          <a-button
            v-else
            type="link" size="small"
            @click="$emit('resume', s)"
          >继续</a-button>
          <a-popconfirm
            title="确定删除此构建记录？"
            ok-text="删除"
            cancel-text="取消"
            @confirm="$emit('delete', s)"
          >
            <a-button type="link" size="small" danger>删除</a-button>
          </a-popconfirm>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BuilderSession, SessionStatus } from '../../../types/builder'

const props = defineProps<{ sessions: BuilderSession[] }>()
defineEmits<{
  (e: 'new'): void
  (e: 'resume', s: BuilderSession): void
  (e: 'view', s: BuilderSession): void
  (e: 'delete', s: BuilderSession): void
}>()

const sortedSessions = computed(() =>
  [...props.sessions].sort((a, b) => (b.updatedAt > a.updatedAt ? 1 : -1)),
)

function stageLabel(status: SessionStatus) {
  return ({
    drafting: '构建中',
    pending_review: '走测中',
    reviewing: '走测中',
    pending_hydration: '水合演练',
    hydrating: '水合演练',
    pending_publish: '发布中',
    publishing: '发布中',
    published: '已发布',
  } as const)[status] || status
}
function stageTone(status: SessionStatus) {
  return ({
    drafting: 'orange',
    pending_review: 'purple',
    reviewing: 'purple',
    pending_hydration: 'teal',
    hydrating: 'teal',
    pending_publish: 'green',
    publishing: 'green',
    published: 'green',
  } as const)[status] || 'slate'
}
function reviewLabel(status: SessionStatus) {
  if (status === 'drafting' || status === 'pending_review') return '待审核'
  if (status === 'reviewing') return '走测中'
  return '已审核'
}
function reviewTone(status: SessionStatus) {
  if (status === 'reviewing') return 'purple'
  if (status === 'drafting' || status === 'pending_review') return 'blue'
  return 'green'
}
function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.ob-recent {
  padding: 32px 40px;
  min-height: calc(100vh - 64px);
}
.ob-recent__header {
  display: flex; justify-content: space-between; align-items: flex-end;
  margin-bottom: 24px;
}
.ob-recent__eyebrow {
  font-size: 12px; color: #4f46e5; font-weight: 600;
  letter-spacing: 0.5px; text-transform: uppercase;
  margin-bottom: 6px;
}
.ob-recent__title {
  font-size: 24px; font-weight: 700; color: #0f172a;
  margin: 0 0 6px;
}
.ob-recent__sub { font-size: 13px; color: #64748b; }
.ob-recent-new-btn {
  display: inline-flex; align-items: center; gap: 8px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; border: 0;
  padding: 10px 20px; border-radius: 10px;
  font-size: 13px; font-weight: 600;
  cursor: pointer;
  box-shadow: 0 6px 16px -4px rgba(79, 70, 229, 0.4);
  transition: transform 150ms ease, box-shadow 150ms ease;
}
.ob-recent-new-btn:hover { transform: translateY(-1px); box-shadow: 0 10px 24px -6px rgba(79, 70, 229, 0.5); }
.ob-recent-new-btn .plus { font-size: 16px; line-height: 1; margin-top: -1px; }

.ob-recent-table {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.ob-recent-row {
  display: grid;
  grid-template-columns:
    minmax(180px, 1.4fr)
    minmax(140px, 1.1fr)
    minmax(100px, 0.9fr)
    minmax(100px, 0.9fr)
    minmax(100px, 0.9fr)
    minmax(80px, 0.7fr)
    minmax(120px, 1fr)
    minmax(140px, 0.9fr);
  gap: 16px;
  padding: 14px 20px;
  font-size: 13px;
  color: #334155;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
}
.ob-recent-row:last-child { border-bottom: 0; }
.ob-recent-row--head {
  background: #f8fafc;
  font-size: 12px; font-weight: 600; color: #64748b;
  letter-spacing: 0.4px;
}
.cell--name .name { font-weight: 600; color: #0f172a; }
.cell--name .meta { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.actions { display: flex; gap: 4px; align-items: center; }

.ob-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  background: #f1f5f9;
  color: #64748b;
}
.ob-tag--ai { background: rgba(99, 102, 241, 0.12); color: #4f46e5; }
.ob-tag--upload { background: rgba(16, 185, 129, 0.12); color: #059669; }
.ob-tag--orange { background: rgba(245, 158, 11, 0.12); color: #d97706; }
.ob-tag--purple { background: rgba(139, 92, 246, 0.12); color: #7c3aed; }
.ob-tag--teal { background: rgba(20, 184, 166, 0.12); color: #0d9488; }
.ob-tag--green { background: rgba(16, 185, 129, 0.12); color: #059669; }
.ob-tag--blue { background: rgba(59, 130, 246, 0.12); color: #2563eb; }
.ob-tag--slate { background: #f1f5f9; color: #64748b; }
</style>
