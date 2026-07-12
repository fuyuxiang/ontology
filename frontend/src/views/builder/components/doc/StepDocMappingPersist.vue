<template>
  <div class="step-persist">
    <h2 class="step-persist__title">映射确认与落库</h2>

    <div v-if="loading" class="step-persist__loading">
      <div class="step-persist__spinner"></div>
      <p>正在加载预览数据...</p>
    </div>

    <div v-else-if="errorMessage" class="step-persist__error">
      <p>{{ errorMessage }}</p>
      <button class="step-persist__btn" @click="loadPreview">重试</button>
    </div>

    <template v-else-if="items.length">
      <!-- 顶部统计 -->
      <div class="step-persist__stats">
        <span class="step-persist__stat step-persist__stat--ok">
          ✓ 已匹配 {{ matchedCount }}/{{ items.length }}
        </span>
        <span v-if="conflictCount" class="step-persist__stat step-persist__stat--warn">
          ⚠ 冲突 {{ conflictCount }}
        </span>
        <span v-if="unregisteredCount" class="step-persist__stat step-persist__stat--error">
          ✗ 未注册 {{ unregisteredCount }}
        </span>
        <span v-if="incompleteItems.length" class="step-persist__stat step-persist__stat--warn">
          ⚠ 字段映射不完整 {{ incompleteItems.length }}
        </span>
      </div>

      <!-- 主体：左列表 + 右明细 -->
      <div class="step-persist__body">
        <!-- 左侧实体列表 -->
        <div class="step-persist__list">
          <div
            v-for="item in items"
            :key="item.entity_name"
            class="step-persist__list-item"
            :class="{
              'step-persist__list-item--active': selectedEntity === item.entity_name,
              'step-persist__list-item--conflict': item.conflict,
              'step-persist__list-item--unregistered': !item.asset_registered,
              'step-persist__list-item--ok': item.asset_registered && !item.conflict,
            }"
            @click="selectedEntity = item.entity_name"
          >
            <span class="step-persist__list-icon">
              <span v-if="item.conflict">⚠</span>
              <span v-else-if="!item.asset_registered">✗</span>
              <span v-else>✓</span>
            </span>
            <span class="step-persist__list-name">{{ item.entity_name }}</span>
            <span v-if="item.table_name" class="step-persist__list-table">{{ item.table_name }}</span>
            <span
              v-if="item.field_mappings.length && mappedFieldCount(item) / item.field_mappings.length < 0.5"
              class="step-persist__list-warn"
              title="字段映射不完整"
            >⚠</span>
          </div>
        </div>

        <!-- 右侧明细 -->
        <div class="step-persist__detail">
          <template v-if="selectedItem">
            <!-- 头部 -->
            <div class="step-persist__detail-header">
              <span class="step-persist__detail-entity">{{ selectedItem.entity_name }}</span>
              <span v-if="selectedItem.table_name" class="step-persist__detail-table">→ {{ selectedItem.table_name }}</span>
              <span class="step-persist__detail-conf">
                置信度 {{ Math.round((selectedItem.confidence || 0) * 100) }}%
              </span>
              <span class="step-persist__detail-conf">
                字段映射 {{ mappedFieldCount(selectedItem) }}/{{ selectedItem.field_mappings.length }}
              </span>
            </div>

            <!-- 字段映射不完整提示 -->
            <div
              v-if="selectedItem.field_mappings.length && mappedFieldCount(selectedItem) / selectedItem.field_mappings.length < 0.5"
              class="step-persist__alert step-persist__alert--warn"
            >
              <strong>字段映射不完整：</strong>该实体仅 {{ mappedFieldCount(selectedItem) }}/{{ selectedItem.field_mappings.length }} 个属性匹配到来源字段，未匹配的属性落库后将没有数据源。可返回上一步手动补全映射。
            </div>

            <!-- 冲突提示 -->
            <div v-if="selectedItem.conflict" class="step-persist__alert step-persist__alert--warn">
              <strong>检测到冲突：</strong>已存在绑定 "{{ selectedItem.conflict.existing_asset_name }}"，请选择处理方式：
              <div class="step-persist__radio-group">
                <label class="step-persist__radio">
                  <input
                    type="radio"
                    :name="'conflict-' + selectedItem.entity_name"
                    value="overwrite"
                    v-model="conflictActions[selectedItem.entity_name]"
                  />
                  覆盖（使用新映射）
                </label>
                <label class="step-persist__radio">
                  <input
                    type="radio"
                    :name="'conflict-' + selectedItem.entity_name"
                    value="keep"
                    v-model="conflictActions[selectedItem.entity_name]"
                  />
                  保留旧的
                </label>
              </div>
            </div>

            <!-- 未注册提示 -->
            <div v-if="!selectedItem.asset_registered" class="step-persist__alert step-persist__alert--error">
              <strong>资产未注册：</strong>该实体对应的数据资产尚未在系统中注册。
              <div class="step-persist__unregistered-actions">
                <button
                  class="step-persist__btn step-persist__btn--sm"
                  :class="{ 'step-persist__btn--active': registerSet.has(selectedItem.entity_name) }"
                  @click="toggleRegister(selectedItem.entity_name)"
                >
                  {{ registerSet.has(selectedItem.entity_name) ? '✓ 已选择注册' : '一键注册' }}
                </button>
                <button
                  class="step-persist__btn step-persist__btn--sm step-persist__btn--secondary"
                  :class="{ 'step-persist__btn--active-secondary': skipSet.has(selectedItem.entity_name) }"
                  @click="toggleSkip(selectedItem.entity_name)"
                >
                  {{ skipSet.has(selectedItem.entity_name) ? '✓ 已跳过' : '跳过' }}
                </button>
              </div>
            </div>

            <!-- 字段映射表 -->
            <table class="step-persist__table">
              <thead>
                <tr>
                  <th>属性名称</th>
                  <th>来源字段</th>
                  <th>置信度</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="fm in selectedItem.field_mappings"
                  :key="fm.attribute_name"
                  :class="{ 'step-persist__row--low': fm.confidence < 0.8 }"
                >
                  <td>{{ fm.attribute_name }}</td>
                  <td>{{ fm.source_column || '-' }}</td>
                  <td>
                    <span
                      class="step-persist__conf"
                      :class="fm.source_column ? (fm.confidence >= 0.8 ? 'step-persist__conf--high' : 'step-persist__conf--low') : 'step-persist__conf--none'"
                    >
                      {{ fm.source_column ? Math.round((fm.confidence || 0) * 100) + '%' : '-' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>
          <div v-else class="step-persist__detail-empty">请在左侧选择一个实体查看映射明细</div>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="step-persist__actions">
        <button class="step-persist__btn step-persist__btn--secondary" @click="emit('prev')">上一步</button>
        <button
          class="step-persist__btn"
          :disabled="applying || hasUnhandledConflicts || hasUnhandledUnregistered"
          @click="onApply"
        >
          <span v-if="applying">
            <span class="step-persist__spinner step-persist__spinner--inline"></span>
            提交中...
          </span>
          <span v-else>确认映射并落库</span>
        </button>
      </div>
      <p v-if="hasUnhandledConflicts" class="step-persist__hint">请处理所有冲突后再继续</p>
      <p v-else-if="hasUnhandledUnregistered" class="step-persist__hint">请对所有未注册资产选择"注册"或"跳过"</p>
    </template>

    <div v-else-if="!loading" class="step-persist__empty">暂无映射数据</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  previewMappingPersist,
  applyMappingPersist,
  type MappingPreviewItem,
  type MappingApplyItem,
} from '../../../../api/docBuilder'

const props = defineProps<{
  sessionId: string
  mappingResult: any
}>()

const emit = defineEmits<{
  prev: []
  next: []
}>()

const loading = ref(false)
const applying = ref(false)
const errorMessage = ref('')
const items = ref<MappingPreviewItem[]>([])
const selectedEntity = ref<string>('')

// conflict: entity_name -> 'overwrite' | 'keep'
const conflictActions = reactive<Record<string, 'overwrite' | 'keep'>>({})
// unregistered: sets of entity names chosen to register or skip
const registerSet = reactive<Set<string>>(new Set())
const skipSet = reactive<Set<string>>(new Set())

const selectedItem = computed(() =>
  items.value.find(i => i.entity_name === selectedEntity.value) ?? null,
)

const matchedCount = computed(() =>
  items.value.filter(i => i.asset_registered && !i.conflict).length,
)

const conflictCount = computed(() => items.value.filter(i => i.conflict).length)

const unregisteredCount = computed(() => items.value.filter(i => !i.asset_registered).length)

// 某实体已成功映射到字段的属性数（attribute_id + source_column 都有值）
function mappedFieldCount(item: MappingPreviewItem): number {
  return (item.field_mappings || []).filter(fm => fm.attribute_id && fm.source_column).length
}

// 字段映射不完整的实体（有属性但一个都没映射上，或映射率低于 50%）——仅统计将要落库的实体
const incompleteItems = computed(() =>
  items.value.filter(i => {
    if (!i.asset_registered && skipSet.has(i.entity_name)) return false // 跳过的不算
    const total = (i.field_mappings || []).length
    if (total === 0) return false
    return mappedFieldCount(i) / total < 0.5
  }),
)

const hasUnhandledConflicts = computed(() =>
  items.value.some(i => i.conflict && !conflictActions[i.entity_name]),
)

const hasUnhandledUnregistered = computed(() =>
  items.value.some(
    i => !i.asset_registered && !registerSet.has(i.entity_name) && !skipSet.has(i.entity_name),
  ),
)

function toggleRegister(name: string) {
  if (registerSet.has(name)) {
    registerSet.delete(name)
  } else {
    registerSet.add(name)
    skipSet.delete(name)
  }
}

function toggleSkip(name: string) {
  if (skipSet.has(name)) {
    skipSet.delete(name)
  } else {
    skipSet.add(name)
    registerSet.delete(name)
  }
}

async function loadPreview() {
  loading.value = true
  errorMessage.value = ''
  try {
    const resp = await previewMappingPersist(props.sessionId, props.mappingResult)
    items.value = resp.items || []
    if (items.value.length) {
      selectedEntity.value = items.value[0].entity_name
    }
    // Pre-fill conflict actions for items that only have one option
    for (const item of items.value) {
      if (item.conflict && !conflictActions[item.entity_name]) {
        conflictActions[item.entity_name] = 'overwrite'
      }
    }
  } catch (e: any) {
    errorMessage.value = `预览失败: ${e?.message || '未知错误'}`
  } finally {
    loading.value = false
  }
}

async function onApply() {
  // 字段映射不完整时，落库前明确提示，避免静默产生「有对象无数据源」的本体
  if (incompleteItems.value.length) {
    const names = incompleteItems.value.map(i => i.entity_name).join('、')
    const ok = window.confirm(
      `以下实体的字段映射不完整，落库后这些属性将没有数据源：\n\n${names}\n\n` +
      `建议返回上一步补全字段映射。是否仍要继续落库？`,
    )
    if (!ok) return
  }

  applying.value = true
  try {
    const applyItems: MappingApplyItem[] = items.value
      .filter(i => {
        // Skip unregistered items that are marked to skip
        if (!i.asset_registered && skipSet.has(i.entity_name)) return false
        return true
      })
      .map(i => ({
        entity_id: i.entity_id,
        asset_id: i.asset_id,
        conflict_action: i.conflict ? (conflictActions[i.entity_name] ?? null) : null,
        register_asset: !i.asset_registered && registerSet.has(i.entity_name),
        table_name: i.table_name,
        field_mappings: (i.field_mappings || [])
          .filter(fm => fm.attribute_id && fm.source_column)
          .map(fm => ({ attribute_id: fm.attribute_id!, source_column: fm.source_column })),
      }))

    const result = await applyMappingPersist(props.sessionId, applyItems)
    message.success(
      `落库成功：新建 ${result.created}，更新 ${result.updated}，跳过 ${result.skipped}`,
    )
    emit('next')
  } catch (e: any) {
    message.error(`落库失败: ${e?.message || '未知错误'}`)
  } finally {
    applying.value = false
  }
}

onMounted(() => {
  loadPreview()
})
</script>

<style scoped>
.step-persist { padding: 24px; max-width: 1100px; margin: 0 auto; }
.step-persist__title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }

/* loading / error */
.step-persist__loading { text-align: center; padding: 60px 0; }
.step-persist__spinner { width: 32px; height: 32px; border: 3px solid #e0e0e0; border-top-color: #4a6fa5; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
.step-persist__spinner--inline { display: inline-block; width: 14px; height: 14px; border-width: 2px; margin: 0 6px 0 0; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }
.step-persist__error { text-align: center; padding: 40px 0; color: #d32f2f; }
.step-persist__empty { text-align: center; padding: 60px 0; color: #999; }

/* stats bar */
.step-persist__stats { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.step-persist__stat { font-size: 13px; font-weight: 600; padding: 4px 10px; border-radius: 4px; }
.step-persist__stat--ok { background: #e8f5e9; color: #2e7d32; }
.step-persist__stat--warn { background: #fff3e0; color: #f57c00; }
.step-persist__stat--error { background: #ffebee; color: #d32f2f; }

/* two-column body */
.step-persist__body { display: flex; gap: 0; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; min-height: 360px; }

/* left list */
.step-persist__list { width: 220px; flex-shrink: 0; border-right: 1px solid #e0e0e0; overflow-y: auto; max-height: 480px; }
.step-persist__list-item { display: flex; align-items: center; gap: 6px; padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #f0f0f0; font-size: 13px; transition: background 0.15s; }
.step-persist__list-item:hover { background: #f5f5f5; }
.step-persist__list-item--active { background: #e8eef7 !important; font-weight: 600; }
.step-persist__list-icon { font-size: 14px; flex-shrink: 0; }
.step-persist__list-item--ok .step-persist__list-icon { color: #2e7d32; }
.step-persist__list-item--conflict .step-persist__list-icon { color: #f57c00; }
.step-persist__list-item--unregistered .step-persist__list-icon { color: #d32f2f; }
.step-persist__list-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.step-persist__list-table { font-size: 11px; color: #888; white-space: nowrap; }
.step-persist__list-warn { font-size: 12px; color: #f57c00; flex-shrink: 0; }

/* right detail */
.step-persist__detail { flex: 1; padding: 16px; overflow-y: auto; max-height: 480px; }
.step-persist__detail-empty { color: #aaa; text-align: center; margin-top: 60px; font-size: 13px; }
.step-persist__detail-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.step-persist__detail-entity { font-size: 15px; font-weight: 600; }
.step-persist__detail-table { color: #4a6fa5; font-size: 13px; }
.step-persist__detail-conf { font-size: 12px; color: #888; margin-left: auto; }

/* alerts */
.step-persist__alert { padding: 10px 14px; border-radius: 5px; font-size: 13px; margin-bottom: 12px; }
.step-persist__alert--warn { background: #fff8e1; border-left: 4px solid #f57c00; }
.step-persist__alert--error { background: #ffebee; border-left: 4px solid #d32f2f; }
.step-persist__radio-group { display: flex; gap: 16px; margin-top: 8px; }
.step-persist__radio { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.step-persist__unregistered-actions { display: flex; gap: 8px; margin-top: 10px; }

/* field mapping table */
.step-persist__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.step-persist__table th, .step-persist__table td { padding: 7px 12px; border: 1px solid #e0e0e0; text-align: left; }
.step-persist__table th { background: #f5f5f5; font-weight: 600; }
.step-persist__row--low { background: #fffde7; }
.step-persist__conf { font-weight: 600; }
.step-persist__conf--high { color: #2e7d32; }
.step-persist__conf--low { color: #f57c00; }
.step-persist__conf--none { color: #999; font-weight: normal; }

/* bottom actions */
.step-persist__actions { display: flex; gap: 12px; justify-content: space-between; margin-top: 20px; }
.step-persist__hint { color: #d32f2f; font-size: 12px; text-align: right; margin-top: 6px; }

/* buttons */
.step-persist__btn { padding: 8px 20px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
.step-persist__btn:disabled { background: #ccc; cursor: not-allowed; }
.step-persist__btn--secondary { background: #fff; color: #4a6fa5; border: 1px solid #4a6fa5; }
.step-persist__btn--secondary:disabled { color: #ccc; border-color: #ccc; cursor: not-allowed; }
.step-persist__btn--sm { padding: 4px 12px; font-size: 12px; }
.step-persist__btn--active { background: #2e7d32; }
.step-persist__btn--active-secondary { background: #fff; color: #888; border-color: #ccc; }
</style>
