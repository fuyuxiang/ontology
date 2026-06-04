<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ruleApi } from '../../api/rules'
import { functionApi } from '../../api/functions'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'
import RuleBuilderDrawer from './RuleBuilderDrawer.vue'
import FunctionBuilderDrawer from './FunctionBuilderDrawer.vue'
import type { BusinessRule } from '../../types'
import type { FunctionItem } from '../../api/functions'

const props = defineProps<{ entityId: string }>()

const toast = useToast()

const rules = ref<BusinessRule[]>([])
const functions = ref<FunctionItem[]>([])
const actions = ref<any[]>([])
const loading = ref(false)

const ruleDrawerVisible = ref(false)
const ruleEditId = ref<string | undefined>()
const fnDrawerVisible = ref(false)
const fnEditId = ref<string | undefined>()

async function fetchData() {
  loading.value = true
  try {
    const [r, f, entity] = await Promise.all([
      ruleApi.list({ entityId: props.entityId }),
      functionApi.list({ entity_id: props.entityId }),
      entityApi.detail(props.entityId),
    ])
    rules.value = r
    functions.value = f
    actions.value = (entity as any).actions ?? []
  } catch (e: any) {
    toast.error(e?.message ?? '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

function openNewRule() { ruleEditId.value = undefined; ruleDrawerVisible.value = true }
function openEditRule(id: string) { ruleEditId.value = id; ruleDrawerVisible.value = true }
function onRuleSaved() { ruleDrawerVisible.value = false; fetchData() }

function openNewFn() { fnEditId.value = undefined; fnDrawerVisible.value = true }
function openEditFn(id: string) { fnEditId.value = id; fnDrawerVisible.value = true }
function onFnSaved() { fnDrawerVisible.value = false; fetchData() }

function priorityLabel(p: string) {
  return p === 'high' ? '高' : p === 'medium' ? '中' : '低'
}
</script>

<template>
  <div class="entity-logic-tab">
    <div v-if="loading" class="logic-empty">加载中…</div>

    <!-- Rules section -->
    <div class="form-section">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <div class="form-section__title" style="margin-bottom:0;">
          规则
          <span style="font-size:12px;font-weight:400;color:var(--neutral-400,#aaa);margin-left:4px;">（{{ rules.length }}）</span>
        </div>
        <button class="btn-sm-exec" @click="openNewRule">+ 新建</button>
      </div>

      <div v-if="!rules.length && !loading" class="logic-empty" style="padding:20px;">暂无规则</div>
      <div v-for="rule in rules" :key="rule.id" class="rule-card" @click="openEditRule(rule.id)">
        <div class="rule-card__header">
          <span class="rule-card__status" :class="`rule-card__status--${rule.status}`"></span>
          <span class="rule-card__name" style="font-weight:500;">{{ rule.name }}</span>
          <span class="rule-card__priority" :class="`priority--${rule.priority}`">{{ priorityLabel(rule.priority) }}</span>
        </div>
      </div>
    </div>

    <!-- Functions section -->
    <div class="form-section">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <div class="form-section__title" style="margin-bottom:0;">
          函数
          <span style="font-size:12px;font-weight:400;color:var(--neutral-400,#aaa);margin-left:4px;">（{{ functions.length }}）</span>
        </div>
        <button class="btn-sm-exec" @click="openNewFn">+ 新建</button>
      </div>

      <div v-if="!functions.length && !loading" class="logic-empty" style="padding:20px;">暂无函数</div>
      <div v-for="fn in functions" :key="fn.id" class="rule-card" @click="openEditFn(fn.id)">
        <div class="rule-card__header">
          <span style="font-size:14px;flex-shrink:0;">ƒ</span>
          <span class="rule-card__name" style="font-weight:500;">{{ fn.name }}</span>
          <code style="font-size:11px;color:var(--neutral-400,#aaa);">{{ fn.callable_name }}</code>
          <span class="rule-card__priority">{{ fn.return_type }}</span>
        </div>
        <div v-if="fn.description" style="margin-top:4px;font-size:12px;color:var(--neutral-500,#888);padding-left:22px;">
          {{ fn.description }}
        </div>
      </div>
    </div>

    <!-- Actions section (read-only) -->
    <div class="form-section">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <div class="form-section__title" style="margin-bottom:0;">
          动作
          <span style="font-size:12px;font-weight:400;color:var(--neutral-400,#aaa);margin-left:4px;">（{{ actions.length }}）</span>
        </div>
      </div>

      <div v-if="!actions.length && !loading" class="logic-empty" style="padding:20px;">暂无动作</div>
      <div v-for="action in actions" :key="action.id" class="rule-card" style="cursor:default;">
        <div class="rule-card__header">
          <span style="font-size:14px;flex-shrink:0;">▶</span>
          <span class="rule-card__name" style="font-weight:500;">{{ action.name }}</span>
          <span class="rule-card__priority">{{ action.type }}</span>
          <span class="rule-card__status" :class="`rule-card__status--${action.status}`"></span>
        </div>
      </div>
    </div>

    <!-- Drawers -->
    <RuleBuilderDrawer
      :visible="ruleDrawerVisible"
      :edit-id="ruleEditId"
      :locked-entity-id="entityId"
      @close="ruleDrawerVisible = false"
      @saved="onRuleSaved"
    />

    <FunctionBuilderDrawer
      :visible="fnDrawerVisible"
      :edit-id="fnEditId"
      :locked-entity-id="entityId"
      @close="fnDrawerVisible = false"
      @saved="onFnSaved"
    />
  </div>
</template>
