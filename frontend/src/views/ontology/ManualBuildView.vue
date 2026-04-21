<template>
  <div class="manual-build">
    <div class="manual-build__header">
      <h2 class="manual-build__title">手工构建本体</h2>
      <p class="manual-build__desc">通过表单手动创建本体对象、定义属性和关系</p>
    </div>

    <a-card class="manual-build__form-card">
      <a-form :model="form" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="英文名称" required>
              <a-input v-model:value="form.name" placeholder="如 CustomerOrder" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="中文名称" required>
              <a-input v-model:value="form.name_cn" placeholder="如 客户订单" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="层级" required>
              <a-radio-group v-model:value="form.tier">
                <a-radio-button :value="1">核心</a-radio-button>
                <a-radio-button :value="2">领域</a-radio-button>
                <a-radio-button :value="3">场景</a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" placeholder="本体对象的业务描述" />
        </a-form-item>

        <!-- 属性列表 -->
        <div class="manual-build__section">
          <div class="manual-build__section-header">
            <span class="manual-build__section-title">属性定义</span>
            <a-button size="small" @click="addAttr">+ 添加属性</a-button>
          </div>
          <a-table :dataSource="form.attributes" :columns="attrColumns" :pagination="false" size="small" row-key="key">
            <template #bodyCell="{ column, record, index }">
              <template v-if="column.dataIndex === 'name'">
                <a-input v-model:value="record.name" size="small" placeholder="属性名" />
              </template>
              <template v-else-if="column.dataIndex === 'type'">
                <a-select v-model:value="record.type" size="small" style="width: 100%">
                  <a-select-option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</a-select-option>
                </a-select>
              </template>
              <template v-else-if="column.dataIndex === 'description'">
                <a-input v-model:value="record.description" size="small" placeholder="说明" />
              </template>
              <template v-else-if="column.dataIndex === 'required'">
                <a-checkbox v-model:checked="record.required" />
              </template>
              <template v-else-if="column.dataIndex === 'action'">
                <a-button type="link" danger size="small" @click="form.attributes.splice(index, 1)">删除</a-button>
              </template>
            </template>
          </a-table>
        </div>

        <!-- 关系定义 -->
        <div class="manual-build__section">
          <div class="manual-build__section-header">
            <span class="manual-build__section-title">关系定义</span>
            <a-button size="small" @click="addRelation">+ 添加关系</a-button>
          </div>
          <a-table :dataSource="relations" :columns="relColumns" :pagination="false" size="small" row-key="key">
            <template #bodyCell="{ column, record, index }">
              <template v-if="column.dataIndex === 'name'">
                <a-input v-model:value="record.name" size="small" placeholder="关系名" />
              </template>
              <template v-else-if="column.dataIndex === 'target'">
                <a-input v-model:value="record.target" size="small" placeholder="目标实体英文名" />
              </template>
              <template v-else-if="column.dataIndex === 'rel_type'">
                <a-select v-model:value="record.rel_type" size="small" style="width: 100%">
                  <a-select-option value="has_one">has_one</a-select-option>
                  <a-select-option value="has_many">has_many</a-select-option>
                  <a-select-option value="belongs_to">belongs_to</a-select-option>
                  <a-select-option value="many_to_many">many_to_many</a-select-option>
                </a-select>
              </template>
              <template v-else-if="column.dataIndex === 'cardinality'">
                <a-select v-model:value="record.cardinality" size="small" style="width: 100%">
                  <a-select-option value="1:1">1:1</a-select-option>
                  <a-select-option value="1:N">1:N</a-select-option>
                  <a-select-option value="N:1">N:1</a-select-option>
                  <a-select-option value="N:N">N:N</a-select-option>
                </a-select>
              </template>
              <template v-else-if="column.dataIndex === 'action'">
                <a-button type="link" danger size="small" @click="relations.splice(index, 1)">删除</a-button>
              </template>
            </template>
          </a-table>
        </div>

        <div class="manual-build__actions">
          <a-button type="primary" :loading="submitting" @click="handleSubmit">创建本体对象</a-button>
          <a-button @click="resetForm">重置</a-button>
        </div>
      </a-form>
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'

const attrTypes = ['string', 'number', 'boolean', 'date', 'json', 'ref', 'computed']
let keySeq = 0

const form = reactive({
  name: '',
  name_cn: '',
  tier: 1 as 1 | 2 | 3,
  description: '',
  attributes: [] as { key: number; name: string; type: string; description: string; required: boolean }[],
})

const relations = ref<{ key: number; name: string; target: string; rel_type: string; cardinality: string }[]>([])
const submitting = ref(false)

const attrColumns = [
  { title: '属性名', dataIndex: 'name', width: 180 },
  { title: '类型', dataIndex: 'type', width: 120 },
  { title: '说明', dataIndex: 'description' },
  { title: '必填', dataIndex: 'required', width: 60 },
  { title: '', dataIndex: 'action', width: 60 },
]

const relColumns = [
  { title: '关系名', dataIndex: 'name', width: 160 },
  { title: '目标实体', dataIndex: 'target', width: 160 },
  { title: '关系类型', dataIndex: 'rel_type', width: 140 },
  { title: '基数', dataIndex: 'cardinality', width: 100 },
  { title: '', dataIndex: 'action', width: 60 },
]

function addAttr() {
  form.attributes.push({ key: keySeq++, name: '', type: 'string', description: '', required: false })
}

function addRelation() {
  relations.value.push({ key: keySeq++, name: '', target: '', rel_type: 'has_many', cardinality: '1:N' })
}

function resetForm() {
  form.name = ''
  form.name_cn = ''
  form.tier = 1
  form.description = ''
  form.attributes = []
  relations.value = []
}

async function handleSubmit() {
  if (!form.name || !form.name_cn) {
    message.warning('请填写英文名称和中文名称')
    return
  }
  submitting.value = true
  try {
    const entity = await entityApi.create({
      name: form.name,
      name_cn: form.name_cn,
      tier: form.tier,
      description: form.description,
      attributes: form.attributes.filter(a => a.name).map(a => ({
        id: '', name: a.name, type: a.type as any, description: a.description, required: a.required,
      })),
    } as any)

    for (const rel of relations.value.filter(r => r.name && r.target)) {
      const targets = await entityApi.list({ search: rel.target })
      const target = targets.find(t => t.name === rel.target)
      if (target) {
        await relationApi.create({
          from_entity_id: entity.id,
          to_entity_id: target.id,
          name: rel.name,
          rel_type: rel.rel_type,
          cardinality: rel.cardinality,
        })
      }
    }

    message.success(`本体对象「${form.name_cn}」创建成功`)
    resetForm()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}
</script>
<style scoped>
.manual-build { padding: 24px; }
.manual-build__header { margin-bottom: 20px; }
.manual-build__title { font-size: 18px; font-weight: 600; margin: 0 0 4px; }
.manual-build__desc { color: var(--neutral-500); font-size: 14px; margin: 0; }
.manual-build__section { margin-top: 20px; }
.manual-build__section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.manual-build__section-title { font-size: 15px; font-weight: 600; }
.manual-build__actions { margin-top: 24px; display: flex; gap: 12px; }
</style>
