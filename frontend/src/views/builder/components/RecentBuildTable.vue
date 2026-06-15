<template>
  <div class="ob-root">
    <div style="flex:1;overflow-y:auto;padding:32px 40px">
      <div class="ob-recent-toolbar">
        <span class="ob-recent-title">最近构建</span>
        <button type="button" class="ob-recent-new-btn" @click="$emit('new')">+ 新建本体</button>
      </div>

      <div class="ob-recent-table-wrap">
        <div class="ob-recent-table">
          <div class="ob-recent-row ob-recent-head">
            <div>本体名称</div>
            <div>构建方式</div>
            <div>当前阶段</div>
            <div>审核状态</div>
            <div>创建人</div>
            <div>更新时间</div>
            <div>操作</div>
          </div>

          <div
            v-for="s in sortedSessions"
            :key="s.sessionId"
            class="ob-recent-row ob-recent-body-row"
          >
            <div class="ob-recent-name-cell">
              <span class="ob-recent-icon" aria-hidden="true">📋</span>
              <span class="ob-recent-name" :title="s.ontologyName">{{ s.ontologyName }}</span>
            </div>
            <div>
              <span :class="['ob-recent-chip', `ob-recent-chip-${methodInfo(s).tone}`]">{{ methodInfo(s).label }}</span>
            </div>
            <div>
              <span :class="['ob-stage', `ob-stage-${stageInfo(s.status).tone}`]">
                <span class="ob-stage-dot"></span>{{ stageInfo(s.status).label }}
              </span>
            </div>
            <div>
              <span :class="['ob-recent-chip', `ob-recent-chip-${reviewInfo(s.status).tone}`]">{{ reviewInfo(s.status).label }}</span>
            </div>
            <div class="ob-recent-muted">{{ s.createdBy }}</div>
            <div class="ob-recent-muted">{{ formatTime(s.updatedAt) }}</div>
            <div class="ob-recent-actions">
              <button type="button" class="ob-recent-action-btn" @click="onPrimary(s)">
                {{ s.status === 'published' ? '查看' : '继续' }}
              </button>
              <a-popconfirm
                title="确定删除此构建记录？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="$emit('delete', s)"
              >
                <button type="button" class="ob-recent-delete-btn" :aria-label="`删除 ${s.ontologyName}`">🗑</button>
              </a-popconfirm>
            </div>
          </div>
        </div>
      </div>
    </div>
    <slot name="modal" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BuilderSession, BuildMethod, SessionStatus } from '../../../types/builder'

const props = defineProps<{ sessions: BuilderSession[] }>()
const emit = defineEmits<{
  (e: 'new'): void
  (e: 'resume', s: BuilderSession): void
  (e: 'view', s: BuilderSession): void
  (e: 'delete', s: BuilderSession): void
}>()

const sortedSessions = computed(() =>
  [...props.sessions].sort((a, b) => (b.updatedAt > a.updatedAt ? 1 : -1)),
)

function stageInfo(status: SessionStatus) {
  return ({
    drafting: { label: '建模中', tone: 'orange' },
    pending_review: { label: '审批中', tone: 'purple' },
    reviewing: { label: '审批中', tone: 'purple' },
    pending_hydration: { label: '验证中', tone: 'teal' },
    hydrating: { label: '验证中', tone: 'teal' },
    pending_publish: { label: '发布中', tone: 'green' },
    publishing: { label: '发布中', tone: 'green' },
    published: { label: '已发布', tone: 'green' },
  } as const)[status] || { label: status, tone: 'slate' }
}

function reviewInfo(status: SessionStatus) {
  if (status === 'reviewing') return { label: '走测中', tone: 'purple' }
  if (status === 'drafting' || status === 'pending_review') return { label: '待审核', tone: 'blue' }
  return { label: '已审核', tone: 'green' }
}

function methodInfo(s: BuilderSession): { label: string; tone: 'green' | 'purple' | 'slate' | 'orange' | 'blue' } {
  const m: BuildMethod = s.buildMethod
  if (m === 'import')  return { label: '文件导入', tone: 'green' }
  if (m === 'extract') return { label: '文档抽取', tone: 'orange' }
  if (m === 'chat')    return { label: '对话生成', tone: 'purple' }
  return { label: '手工建模', tone: 'blue' }
}

function formatTime(iso: string) {
  const t = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())} ${pad(t.getHours())}:${pad(t.getMinutes())}`
}

function onPrimary(s: BuilderSession) {
  if (s.status === 'published') emit('view', s)
  else emit('resume', s)
}
</script>
