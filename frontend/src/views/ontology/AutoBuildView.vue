<template>
  <div class="auto-build">
    <div class="auto-build__header">
      <h2 class="auto-build__title">AI 智能构建本体</h2>
      <p class="auto-build__desc">输入业务描述文本或上传文档，AI 自动提取实体、属性和关系</p>
    </div>

    <!-- 输入区 -->
    <a-card class="auto-build__input-card">
      <a-tabs v-model:activeKey="inputMode">
        <a-tab-pane key="text" tab="文本输入">
          <a-textarea
            v-model:value="textInput"
            :rows="8"
            placeholder="请输入业务描述文本，例如：&#10;客户（Customer）是系统的核心实体，包含姓名、手机号、等级等属性。&#10;每个客户可以有多个订单（Order），订单包含订单号、金额、状态等。&#10;客户还关联一个账户（Account），记录余额和积分信息。"
          />
        </a-tab-pane>
        <a-tab-pane key="file" tab="文件上传">
          <a-upload-dragger
            :beforeUpload="handleFileSelect"
            :fileList="fileList"
            :maxCount="1"
            accept=".txt,.md,.doc,.docx,.pdf"
          >
            <p class="ant-upload-drag-icon"><inbox-outlined /></p>
            <p class="ant-upload-text">点击或拖拽文件到此区域</p>
            <p class="ant-upload-hint">支持 txt、md、doc、docx、pdf 格式</p>
          </a-upload-dragger>
        </a-tab-pane>
      </a-tabs>

      <div class="auto-build__extract-bar">
        <a-button type="primary" :loading="extracting" @click="handleExtract">
          AI 提取本体
        </a-button>
      </div>
    </a-card>
    <!-- 提取结果 -->
    <template v-if="result">
      <a-card class="auto-build__result-card" title="提取结果预览">
        <template #extra>
          <a-space>
            <a-tag color="blue">{{ result.entities.length }} 个实体</a-tag>
            <a-tag color="green">{{ totalAttrs }} 个属性</a-tag>
            <a-tag color="orange">{{ result.relations.length }} 个关系</a-tag>
          </a-space>
        </template>

        <div v-for="(entity, ei) in result.entities" :key="ei" class="auto-build__entity">
          <div class="auto-build__entity-header">
            <a-checkbox v-model:checked="entity.selected" />
            <span class="auto-build__entity-name">{{ entity.name }}</span>
            <a-tag size="small">{{ entity.name_cn }}</a-tag>
            <a-tag :color="tierColor(entity.tier)" size="small">Tier {{ entity.tier }}</a-tag>
            <a-input v-model:value="entity.description" size="small" style="flex:1; margin-left:8px" placeholder="描述" />
          </div>
          <a-table
            :dataSource="entity.attributes"
            :columns="attrPreviewCols"
            :pagination="false"
            size="small"
            class="auto-build__attr-table"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'name'">
                <a-input v-model:value="record.name" size="small" />
              </template>
              <template v-else-if="column.dataIndex === 'type'">
                <a-select v-model:value="record.type" size="small" style="width:100%">
                  <a-select-option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</a-select-option>
                </a-select>
              </template>
              <template v-else-if="column.dataIndex === 'description'">
                <a-input v-model:value="record.description" size="small" />
              </template>
            </template>
          </a-table>
        </div>

        <div v-if="result.relations.length" class="auto-build__relations">
          <h4>关系</h4>
          <a-table :dataSource="result.relations" :columns="relPreviewCols" :pagination="false" size="small" />
        </div>

        <div class="auto-build__actions">
          <a-button type="primary" :loading="creating" @click="handleCreate">
            确认创建 ({{ selectedCount }} 个实体)
          </a-button>
          <a-button @click="result = null">放弃</a-button>
        </div>
      </a-card>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import { post } from '../../api/client'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import type { UploadFile } from 'ant-design-vue'

interface ExtractedAttr { name: string; type: string; description: string }
interface ExtractedEntity { name: string; name_cn: string; tier: number; description: string; attributes: ExtractedAttr[]; selected: boolean }
interface ExtractedRelation { from_entity: string; to_entity: string; name: string; rel_type: string; cardinality: string }
interface ExtractResult { entities: ExtractedEntity[]; relations: ExtractedRelation[] }

const attrTypes = ['string', 'number', 'boolean', 'date', 'json', 'ref', 'computed']
const inputMode = ref('text')
const textInput = ref('')
const fileList = ref<UploadFile[]>([])
const extracting = ref(false)
const creating = ref(false)
const result = ref<ExtractResult | null>(null)

const totalAttrs = computed(() => result.value?.entities.reduce((s, e) => s + e.attributes.length, 0) ?? 0)
const selectedCount = computed(() => result.value?.entities.filter(e => e.selected).length ?? 0)

const attrPreviewCols = [
  { title: '属性名', dataIndex: 'name', width: 160 },
  { title: '类型', dataIndex: 'type', width: 110 },
  { title: '说明', dataIndex: 'description' },
]
const relPreviewCols = [
  { title: '源实体', dataIndex: 'from_entity', width: 140 },
  { title: '目标实体', dataIndex: 'to_entity', width: 140 },
  { title: '关系名', dataIndex: 'name', width: 140 },
  { title: '类型', dataIndex: 'rel_type', width: 120 },
  { title: '基数', dataIndex: 'cardinality', width: 80 },
]

function tierColor(tier: number) { return tier === 1 ? 'blue' : tier === 2 ? 'green' : 'orange' }

function handleFileSelect(file: File) {
  fileList.value = [{ uid: '-1', name: file.name, status: 'done', originFileObj: file } as any]
  return false
}

async function handleExtract() {
  if (inputMode.value === 'text' && !textInput.value.trim()) {
    message.warning('请输入业务描述文本')
    return
  }
  if (inputMode.value === 'file' && !fileList.value.length) {
    message.warning('请上传文件')
    return
  }
  extracting.value = true
  try {
    let data: ExtractResult
    if (inputMode.value === 'text') {
      data = await post<ExtractResult>('/entities/ai-extract', { text: textInput.value })
    } else {
      const fd = new FormData()
      fd.append('file', (fileList.value[0] as any).originFileObj)
      data = await post<ExtractResult>('/entities/ai-extract', fd)
    }
    data.entities.forEach(e => { e.selected = true })
    result.value = data
    message.success(`AI 提取完成：${data.entities.length} 个实体`)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || 'AI 提取失败')
  } finally {
    extracting.value = false
  }
}
async function handleCreate() {
  if (!result.value || selectedCount.value === 0) return
  creating.value = true
  const created: Record<string, string> = {}
  try {
    for (const entity of result.value.entities.filter(e => e.selected)) {
      const res = await entityApi.create({
        name: entity.name,
        name_cn: entity.name_cn,
        tier: entity.tier as any,
        description: entity.description,
        attributes: entity.attributes.map(a => ({
          id: '', name: a.name, type: a.type as any, description: a.description, required: false,
        })),
      } as any)
      created[entity.name] = res.id
    }
    for (const rel of result.value.relations) {
      const fromId = created[rel.from_entity]
      const toId = created[rel.to_entity]
      if (fromId && toId) {
        await relationApi.create({
          from_entity_id: fromId,
          to_entity_id: toId,
          name: rel.name,
          rel_type: rel.rel_type,
          cardinality: rel.cardinality,
        })
      }
    }
    message.success(`成功创建 ${Object.keys(created).length} 个本体对象`)
    result.value = null
    textInput.value = ''
    fileList.value = []
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.auto-build { padding: 24px; }
.auto-build__header { margin-bottom: 20px; }
.auto-build__title { font-size: 18px; font-weight: 600; margin: 0 0 4px; }
.auto-build__desc { color: var(--neutral-500); font-size: 14px; margin: 0; }
.auto-build__extract-bar { margin-top: 16px; text-align: right; }
.auto-build__result-card { margin-top: 20px; }
.auto-build__entity { margin-bottom: 16px; border: 1px solid var(--neutral-200); border-radius: 8px; padding: 12px; }
.auto-build__entity-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.auto-build__entity-name { font-weight: 600; font-size: 15px; }
.auto-build__attr-table { margin-left: 24px; }
.auto-build__relations { margin-top: 16px; }
.auto-build__relations h4 { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.auto-build__actions { margin-top: 20px; display: flex; gap: 12px; }
</style>
