<template>
  <div class="step1-import">
    <div class="step1-import__inner">
      <div class="step1-import__header">
        <div class="step1-import__title">本体导入</div>
        <div class="step1-import__sub">上传 OWL / JSON 本体文件，系统会解析对象、属性与关系，进入导入审核流程</div>
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
        <div class="import-drop__sub">支持 .owl / .json / .ttl / .rdf — 最大 50MB</div>
        <input ref="fileInput" type="file" class="hidden-file" accept=".owl,.json,.ttl,.rdf" @change="onFileChange" />
      </div>

      <div v-if="parsedSummary" class="import-summary">
        <div class="import-summary__head">
          <div class="import-summary__title">解析结果</div>
          <a-tag color="green">已解析</a-tag>
        </div>
        <div class="import-summary__grid">
          <div class="import-summary__card">
            <div class="card-num">{{ parsedSummary.classCount }}</div>
            <div class="card-label">对象类型</div>
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
import { useBuilderStore, buildPresetClasses, buildPresetRelations } from '../../../store/builder'
import type { BuilderSession, OntologyClassDraft } from '../../../types/builder'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'next'): void }>()
const store = useBuilderStore()

const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const parsedSummary = ref<{
  classCount: number
  relationCount: number
  propertyCount: number
  fileSize: string
  preview: OntologyClassDraft[]
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
  await new Promise(r => setTimeout(r, 1200))
  const classes = buildPresetClasses(props.session.scenarioId)
  const relations = buildPresetRelations(props.session.scenarioId, classes)
  const propertyCount = classes.reduce((sum, c) => sum + c.properties.length, 0)
  parsedSummary.value = {
    classCount: classes.length,
    relationCount: relations.length,
    propertyCount,
    fileSize: (file.size / 1024).toFixed(1) + ' KB',
    preview: classes.slice(0, 10),
  }
  store.patchActive({
    ontologyClasses: classes,
    ontologyRelations: relations,
  })
  store.addUploadRecord({
    fileName: file.name,
    fileType: (file.name.split('.').pop() || 'OWL').toUpperCase(),
    fileSize: (file.size / 1024).toFixed(0) + ' KB',
    sourceOntology: props.session.ontologyName,
    scenarioName: props.session.scenarioName,
    status: 'completed',
    statusText: `已提取 ${classes.length} 对象、${relations.length} 关系`,
    extractedSummary: '本体定义已解析',
    extractedRules: 0,
    extractedFields: propertyCount,
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
