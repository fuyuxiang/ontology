<template>
  <div class="ob-new-modal-mask" @click.self="emit('update:open', false)">
    <div class="ob-new-modal" @click.stop>
      <div class="ob-new-modal-head">
        <h2>{{ methodFixed ? `新建本体 · ${fixedMethodTitle}` : '新建本体' }}</h2>
        <button type="button" class="ob-new-close" aria-label="关闭新建本体弹窗" @click="emit('update:open', false)">×</button>
      </div>

      <div v-if="!methodFixed" class="ob-new-steps">
        <template v-for="(s, idx) in stepDefs" :key="s.num">
          <div :class="['ob-new-step', { active: step === s.num, done: step > s.num }]">
            <span class="ob-new-step-num">{{ s.num }}</span>
            <span>{{ s.label }}</span>
          </div>
          <div v-if="idx < stepDefs.length - 1" :class="['ob-new-step-line', { done: step > s.num }]"></div>
        </template>
      </div>

      <!-- 未锁方式时，第一步 = 选构建方式 -->
      <div v-if="!methodFixed && step === 1" class="ob-new-panel">
        <div class="ob-method-grid ob-method-grid--four">
          <div
            v-for="m in METHOD_CARDS"
            :key="m.id"
            role="button"
            tabindex="0"
            :class="['ob-method-card', `ob-method-${m.tone}`, { selected: form.buildMethod === m.id }]"
            @click="form.buildMethod = m.id"
            @keydown="onMethodKey($event, m.id)"
          >
            <span class="ob-method-icon">{{ m.short }}</span>
            <strong>{{ m.title }}</strong>
            <span>{{ m.subtitle }}</span>
            <em>{{ m.audience }}</em>
          </div>
        </div>
        <div v-if="form.buildMethod" class="ob-method-note">
          下一步给本体起个名字。
        </div>
      </div>

      <!-- 命名 -->
      <div v-if="step === lastStep" class="ob-new-panel">
        <label class="ob-new-label" for="new-onto-name">本体名称 <span>*</span></label>
        <input
          id="new-onto-name"
          :class="['ob-new-input', { 'ob-new-input-error': !!nameError }]"
          v-model="form.ontologyName"
          placeholder="例如：政企客户经营、网络故障域"
          autofocus
        />
        <div v-if="nameError" class="ob-new-field-error">{{ nameError }}</div>

        <div class="ob-quick-box">
          <div class="ob-quick-title">快速填入</div>
          <div class="ob-quick-list">
            <button
              v-for="p in QUICK_TITLES"
              :key="p"
              type="button"
              class="ob-quick-pill"
              @click="form.ontologyName = p"
            >{{ p }}</button>
          </div>
        </div>

        <div class="ob-new-tip">
          构建方式：<strong>{{ currentMethodTitle }}</strong>。开始构建后会进入对应的 Step1 步骤；本体可在多个业务场景中被复用。
        </div>
      </div>

      <div class="ob-new-footer">
        <button v-if="step === 1" type="button" class="ob-new-secondary" @click="emit('update:open', false)">取消</button>
        <button v-else type="button" class="ob-new-secondary" @click="step--">上一步</button>

        <button
          v-if="step < lastStep"
          type="button"
          class="ob-new-primary"
          :disabled="!canNext"
          @click="next"
        >下一步</button>
        <button
          v-else
          type="button"
          class="ob-new-primary"
          :disabled="!canNext"
          @click="submit"
        >开始构建</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { BuildMethod } from '../../../types/builder'

const props = defineProps<{ open: boolean; defaultMethod?: BuildMethod }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'submit', payload: { ontologyName: string; buildMethod: BuildMethod }): void
}>()

const QUICK_TITLES = ['政企客户经营', '退单根因', '网络故障域', 'FTTR 续约']

interface MethodCard {
  id: BuildMethod
  short: string
  title: string
  subtitle: string
  audience: string
  tone: string
}
const METHOD_CARDS: MethodCard[] = [
  { id: 'manual',  short: '手工', title: '手工建模', subtitle: '逐项定义对象、属性、关系',          audience: '适合本体工程师',  tone: 'manual'  },
  { id: 'import',  short: '导入', title: '文件导入', subtitle: 'OWL / RDF / JSON 标准本体文件',     audience: '适合本体工程师',  tone: 'import'  },
  { id: 'extract', short: '抽取', title: '文档抽取', subtitle: 'Word / Excel / PDF 业务文档 LLM 抽取', audience: '适合业务专家',    tone: 'extract' },
  { id: 'chat',    short: '对话', title: '对话生成', subtitle: '对话式联动数据资产与文档生成',        audience: '适合业务分析师',  tone: 'chat'    },
]

// EmptyWelcome 卡片传入了 defaultMethod → 锁定方式，弹窗只剩命名一步
const methodFixed = computed(() => !!props.defaultMethod)
const fixedMethodTitle = computed(() => METHOD_CARDS.find(m => m.id === props.defaultMethod)?.title || '')
const currentMethodTitle = computed(() => METHOD_CARDS.find(m => m.id === form.buildMethod)?.title || '')

const stepDefs = computed(() => methodFixed.value
  ? [{ num: 1, label: '命名' }]
  : [{ num: 1, label: '构建方式' }, { num: 2, label: '命名' }],
)
const lastStep = computed(() => methodFixed.value ? 1 : 2)

const step = ref(1)
const form = reactive<{ ontologyName: string; buildMethod: BuildMethod }>({
  ontologyName: '',
  buildMethod: 'manual',
})
const nameError = ref('')

watch(() => props.open, (v) => {
  if (!v) return
  step.value = 1
  form.ontologyName = ''
  form.buildMethod = props.defaultMethod || 'manual'
  nameError.value = ''
}, { immediate: true })

const canNext = computed(() => {
  if (!methodFixed.value && step.value === 1) return !!form.buildMethod
  return !!form.ontologyName.trim() && !nameError.value
})

watch(() => form.ontologyName, (v) => {
  if (!v.trim()) { nameError.value = ''; return }
  nameError.value = ''
})

function next() {
  if (!canNext.value) return
  if (step.value < lastStep.value) step.value++
}

function onMethodKey(e: KeyboardEvent, m: BuildMethod) {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); form.buildMethod = m }
}

function submit() {
  if (!form.ontologyName.trim()) { nameError.value = '本体名称不能为空'; return }
  emit('submit', { ...form })
}
</script>

<style scoped>
.ob-new-tip {
  margin-top: 16px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}
.ob-new-tip strong { color: #1e293b; }
.ob-method-grid--four {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.ob-method-card.ob-method-extract { border-color: #fb923c; }
.ob-method-card.ob-method-extract.selected { border-color: #ea580c; box-shadow: 0 4px 12px -2px rgba(234,88,12,0.3); }
.ob-method-card.ob-method-extract .ob-method-icon { background: linear-gradient(135deg, #fb923c, #ea580c); color: #fff; }
.ob-method-card.ob-method-manual { border-color: #6366f1; }
.ob-method-card.ob-method-manual.selected { border-color: #4f46e5; box-shadow: 0 4px 12px -2px rgba(79,70,229,0.3); }
.ob-method-card.ob-method-manual .ob-method-icon { background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; }
.ob-method-card.ob-method-chat { border-color: #8b5cf6; }
.ob-method-card.ob-method-chat.selected { border-color: #7c3aed; box-shadow: 0 4px 12px -2px rgba(124,58,237,0.3); }
.ob-method-card.ob-method-chat .ob-method-icon { background: linear-gradient(135deg, #8b5cf6, #6366f1); color: #fff; }
.ob-method-card.ob-method-import { border-color: #10b981; }
.ob-method-card.ob-method-import.selected { border-color: #059669; box-shadow: 0 4px 12px -2px rgba(16,185,129,0.3); }
.ob-method-card.ob-method-import .ob-method-icon { background: linear-gradient(135deg, #10b981, #059669); color: #fff; }
</style>
