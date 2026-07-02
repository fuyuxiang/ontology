<template>
  <div class="step1-import">
    <div class="step1-import__inner">
      <div class="step1-import__header">
        <div class="step1-import__title">文件导入</div>
        <div class="step1-import__sub">导入 OWL / RDF / JSON 标准本体文件或 Excel 模板，系统会解析对象、属性与关系，进入审核流程</div>
      </div>

      <div
        class="import-drop"
        :class="{ 'import-drop--active': dragOver }"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
        @click="fileInput?.click()"
      >
        <div class="import-drop__icon">📤</div>
        <div class="import-drop__title">点击或拖拽文件到此区域</div>
        <div class="import-drop__sub">支持 .owl / .json / .ttl / .rdf / .xlsx — 最大 50MB</div>
        <input ref="fileInput" type="file" class="hidden-file" accept=".owl,.json,.ttl,.rdf,.xlsx,.xls" @change="onFileChange" />
      </div>

      <div v-if="parsedSummary" class="import-summary">
        <div class="import-summary__head">
          <div class="import-summary__title">解析结果</div>
          <a-tag color="green">已解析</a-tag>
        </div>
        <div class="import-summary__grid">
          <div class="import-summary__card">
            <div class="card-num">{{ parsedSummary.classCount }}</div>
            <div class="card-label">对象</div>
          </div>
          <div class="import-summary__card">
            <div class="card-num">{{ parsedSummary.relationCount }}</div>
            <div class="card-label">关联关系</div>
          </div>
          <div class="import-summary__card">
            <div class="card-num">{{ parsedSummary.propertyCount }}</div>
            <div class="card-label">属性总数</div>
          </div>
          <div class="import-summary__card">
            <div class="card-num">{{ parsedSummary.actionCount }}</div>
            <div class="card-label">动作</div>
          </div>
          <div class="import-summary__card">
            <div class="card-num">{{ parsedSummary.fileSize }}</div>
            <div class="card-label">文件大小</div>
          </div>
        </div>

        <div class="import-summary__list">
          <div class="import-summary__list-title">本体对象（前 10 个）</div>
          <div class="import-class-list">
            <div v-for="c in parsedSummary.preview" :key="c.id" class="import-class-card">
              <div class="icc-icon" :class="`icc-icon--t${c.tier}`">{{ c.icon }}</div>
              <div>
                <div class="icc-name">{{ c.displayName }}</div>
                <div class="icc-en">{{ c.name }} · {{ c.properties.length }} 属性</div>
              </div>
            </div>
          </div>
        </div>

        <div class="import-actions">
          <a-button @click="parsedSummary = null">重新选择文件</a-button>
          <a-button type="primary" size="large" @click="confirmImport">
            确认导入 · 已有本体 →
          </a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import type { BuilderSession, OntologyObjectDraft, OntologyRelationDraft } from '../../../types/builder'
import { entityApi } from '../../../api/ontology'
import type { OntologyPreviewResult } from '../../../api/ontology'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'next'): void }>()
const store = useBuilderStore()

const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const parsedSummary = ref<{
  classCount: number
  relationCount: number
  propertyCount: number
  actionCount: number
  fileSize: string
  preview: OntologyObjectDraft[]
} | null>(null)

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (!e.dataTransfer?.files.length) return
  parseFile(e.dataTransfer.files[0])
}
function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) parseFile(f)
}

async function parseFile(file: File) {
  message.loading({ content: '正在解析本体文件...', key: 'parse', duration: 0 })

  const ext = (file.name.split('.').pop() || '').toLowerCase()
  const supported = ['json', 'xlsx', 'xls', 'owl', 'rdf', 'xml', 'ttl']
  if (!supported.includes(ext)) {
    parsedSummary.value = null
    message.error({ content: `不支持的文件格式 .${ext}，请上传 .json / .xlsx / .owl / .ttl / .rdf 文件`, key: 'parse' })
    return
  }

  try {
    // 统一走后端预览接口（只解析不落库），json / excel / owl / ttl 复用同一套草稿映射
    // namespace 留空，由后端推导（json 取 scenario.namespace，excel/owl 不需要）
    const preview: OntologyPreviewResult = await entityApi.previewFile(file, ext)

    if (!preview.objects.length) {
      parsedSummary.value = null
      const tip = ext === 'json'
        ? '未在 JSON 中找到 object_types / entities 定义'
        : (ext === 'xlsx' || ext === 'xls')
          ? '未在 Excel 中解析到对象信息，请检查模板表头是否正确'
          : '未在本体文件中解析到 owl:Class 定义'
      message.error({ content: tip, key: 'parse' })
      return
    }

    const stamp = Date.now().toString(36)
    const nameToId = new Map<string, string>()
    const classes: OntologyObjectDraft[] = preview.objects.map((o, i) => {
      const id = `obj-${stamp}-${i}`
      nameToId.set(o.name, id)
      return {
        id,
        name: o.name,
        displayName: o.display_name || o.name,
        tier: (o.tier || 3) as 1 | 2 | 3,
        namespace: o.namespace || undefined,
        description: o.description || '',
        primaryKey: o.primary_key || 'id',
        icon: '🔷',
        instanceCount: 0,
        backing_asset_ids: [],
        properties: o.properties.map((p, pi) => ({
          id: `prop-${stamp}-${i}-${pi}`,
          name: p.name,
          displayName: p.display_name || p.name,
          type: p.type || 'string',
          required: !!p.required,
          description: p.description || '',
          source_asset_id: null,
          source_column: p.source_field || null,
          source_field: p.source_field || null,
          source_table: p.source_table || null,
        })),
        derivedProperties: [],
        rules: [],
        actions: [],
        approved: false,
      }
    })

    // 基数归一：后端已归一（1:N / N:1 / 1:1 / N:N），N:1 在草稿模型里折叠为 1:N
    const toDraftCardinality = (c: string): '1:1' | '1:N' | 'N:N' =>
      c === 'N:N' ? 'N:N' : c === '1:1' ? '1:1' : '1:N'

    const relations: OntologyRelationDraft[] = preview.relations.map((r, i) => ({
      id: `rel-${stamp}-${i}`,
      name: r.name || `relation_${i}`,
      displayName: r.display_name || r.name || `关系${i + 1}`,
      source: nameToId.get(r.source)!,
      target: nameToId.get(r.target)!,
      cardinality: toDraftCardinality(r.cardinality),
      description: r.description || '',
      relationType: 'ObjectProperty' as const,
      semanticType: 'association' as const,
    }))

    // actions 按 target_object 挂到对应对象（仅记录名称，发布链路再落库）
    const objByName = new Map(classes.map(c => [c.name, c]))
    preview.actions.forEach(a => {
      if (a.target_object && objByName.has(a.target_object)) {
        objByName.get(a.target_object)!.actions.push(a.display_name || a.name)
      }
    })

    const skipped = preview.summary.relation_count < preview.relations.length
    if (skipped) {
      message.warning('部分关系因实体缺失被跳过')
    }

    parsedSummary.value = {
      classCount: preview.summary.object_count,
      relationCount: preview.summary.relation_count,
      propertyCount: preview.summary.property_count,
      actionCount: preview.summary.action_count,
      fileSize: (file.size / 1024).toFixed(1) + ' KB',
      preview: classes.slice(0, 10),
    }
    store.patchActive({
      ontologyObjects: classes,
      ontologyRelations: relations,
    })
  } catch (e: any) {
    parsedSummary.value = null
    message.error({ content: `本体文件解析失败: ${e?.response?.data?.detail || e?.message || '未知错误'}`, key: 'parse' })
    return
  }

  store.addUploadRecord({
    fileName: file.name,
    fileType: ext.toUpperCase() || 'JSON',
    fileSize: (file.size / 1024).toFixed(0) + ' KB',
    sourceOntology: props.session.ontologyName,
    scenarioName: props.session.scenarioName || props.session.ontologyName,
    status: 'completed',
    statusText: `已提取 ${parsedSummary.value!.classCount} 对象、${parsedSummary.value!.relationCount} 关系`,
    extractedSummary: '本体定义已解析',
    extractedRules: 0,
    extractedFields: parsedSummary.value!.propertyCount,
    mimeCategory: 'structured',
  })
  message.success({ content: '本体文件解析完成', key: 'parse' })
}

function confirmImport() {
  if (!parsedSummary.value) return
  store.patchActive({ status: 'pending_review' })
  emit('next')
}
</script>

<style scoped>
.step1-import {
  height: calc(100vh - 64px - 56px - 76px);
  overflow: auto;
  padding: 32px 40px;
}
.step1-import__inner { max-width: 880px; margin: 0 auto; }
.step1-import__header { margin-bottom: 24px; }
.step1-import__title { font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 6px; }
.step1-import__sub { font-size: 13px; color: #64748b; }

.import-drop {
  border: 2px dashed #cbd5e1;
  border-radius: 16px;
  background: #fff;
  padding: 56px 24px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  cursor: pointer;
  transition: all 150ms ease;
}
.import-drop--active,
.import-drop:hover { border-color: #4f46e5; background: rgba(79, 70, 229, 0.04); }
.import-drop__icon { font-size: 40px; }
.import-drop__title { font-size: 14px; font-weight: 600; color: #1e293b; }
.import-drop__sub { font-size: 12px; color: #94a3b8; }
.hidden-file { display: none; }

.import-summary {
  margin-top: 20px;
  padding: 20px 24px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}
.import-summary__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.import-summary__title { font-size: 15px; font-weight: 600; color: #0f172a; }
.import-summary__grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
  margin-bottom: 20px;
}
.import-summary__card {
  background: #f8fafc; border-radius: 10px; padding: 14px;
}
.card-num { font-size: 22px; font-weight: 700; color: #0f172a; line-height: 1.2; }
.card-label { font-size: 11px; color: #94a3b8; margin-top: 4px; }

.import-summary__list-title { font-size: 12px; color: #94a3b8; margin-bottom: 8px; font-weight: 500; }
.import-class-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.import-class-card {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 8px;
  background: #f8fafc;
}
.icc-icon { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 12px; }
.icc-icon--t1 { background: linear-gradient(135deg, #4c6ef5, #364fc7); }
.icc-icon--t2 { background: linear-gradient(135deg, #7950f2, #5f3dc4); }
.icc-icon--t3 { background: linear-gradient(135deg, #20c997, #087f5b); }
.icc-name { font-size: 12px; font-weight: 600; color: #0f172a; }
.icc-en { font-size: 10px; color: #94a3b8; }

.import-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 16px; }
</style>
