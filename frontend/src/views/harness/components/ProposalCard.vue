<template>
  <a-card size="small"
    :style="{ marginBottom: '10px', borderRadius: '8px', border: `1px solid ${isApproved ? '#b7eb8f' : isRejected ? '#ffa39e' : '#f0f0f0'}`, transition: 'border-color 0.3s ease' }"
    :body-style="{ padding: '10px 12px' }">
    <div class="prop-card__head">
      <a-space :size="4">
        <a-tag :icon="h(typeMeta.icon)" :color="typeMeta.color" :style="{ borderRadius: '6px', fontSize: '11px' }">
          {{ typeMeta.text }}
        </a-tag>
        <span class="prop-card__sev" :style="{ background: sevMeta.bg, color: sevMeta.color }">{{ sevMeta.text }}</span>
        <a-tag v-if="isApproved" color="success" :icon="h(CheckCircleOutlined)" :style="{ borderRadius: '6px', fontSize: '11px' }">已批准</a-tag>
        <a-tag v-if="isRejected" color="error" :icon="h(CloseCircleOutlined)" :style="{ borderRadius: '6px', fontSize: '11px' }">已拒绝</a-tag>
      </a-space>
      <a-space v-if="allowAction && proposal.status === 'pending'" :size="4">
        <a-button type="primary" size="small" :icon="h(CheckCircleOutlined)"
          :loading="loadingId === proposal.id"
          @click="$emit('approve')"
          :style="{ fontSize: '11px', height: '24px' }">
          批准
        </a-button>
        <a-button size="small" :icon="h(CloseCircleOutlined)"
          :loading="loadingId === proposal.id"
          @click="$emit('reject')"
          :style="{ fontSize: '11px', height: '24px' }">
          拒绝
        </a-button>
      </a-space>
    </div>
    <a-typography-text strong style="font-size:13px;line-height:1.4">{{ proposal.title }}</a-typography-text>
    <div><a-typography-text type="secondary" style="font-size:11px">{{ proposal.description }}</a-typography-text></div>
    <ImpactRow :impact="proposal.impact" />
    <div v-if="isApproved" class="prop-card__approved">
      <CheckCircleOutlined style="color:#52c41a;font-size:13px" />
      <span style="font-size:11px;color:#333;font-weight:500">提案已批准</span>
      <span style="color:#999;font-size:11px">→</span>
      <span class="prop-card__link" @click="$emit('goto')">在本体工作室中查看变更效果</span>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import {
  SettingOutlined,
  PlusCircleOutlined,
  SyncOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons-vue'
import type { ProposalInfo } from '../../../api/harness'
import ImpactRow from './ImpactRow.vue'

const props = defineProps<{
  proposal: ProposalInfo
  allowAction: boolean
  loadingId: string | null
}>()

defineEmits<{ (e: 'approve'): void; (e: 'reject'): void; (e: 'goto'): void }>()

const TYPE_MAP: Record<string, { color: string; icon: any; text: string }> = {
  rule_tuning: { color: 'orange', icon: SettingOutlined, text: '规则调优' },
  new_attribute: { color: 'blue', icon: PlusCircleOutlined, text: '新增属性' },
  model_retrain: { color: 'purple', icon: SyncOutlined, text: '模型重训' },
  touchpoint_update: { color: 'cyan', icon: InfoCircleOutlined, text: '触点更新' },
}

const SEV_MAP: Record<string, { color: string; bg: string; text: string }> = {
  high: { color: '#ff4d4f', bg: '#fff2f0', text: '高' },
  medium: { color: '#faad14', bg: '#fffbe6', text: '中' },
  low: { color: '#1677ff', bg: '#e6f4ff', text: '低' },
}

const typeMeta = computed(() => TYPE_MAP[props.proposal.type] || TYPE_MAP.rule_tuning)
const sevMeta = computed(() => SEV_MAP[props.proposal.severity] || SEV_MAP.low)
const isApproved = computed(() => props.proposal.status === 'approved')
const isRejected = computed(() => props.proposal.status === 'rejected')
</script>

<style scoped>
.prop-card__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.prop-card__sev {
  font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 600;
}
.prop-card__approved {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  background: linear-gradient(135deg, rgba(82,196,26,0.08) 0%, rgba(22,119,255,0.08) 100%);
  border: 1px solid rgba(82,196,26,0.2);
  display: flex; align-items: center; gap: 6px;
}
.prop-card__link {
  font-size: 11px;
  color: #1677ff;
  cursor: pointer;
  font-weight: 600;
  text-decoration: underline dotted;
  text-underline-offset: 3px;
}
</style>
