<template>
  <div class="create-page">
    <OntologyBreadcrumb :items="breadcrumbs" />

    <div class="create-page__header">
      <h1 class="create-page__title">新建本体对象</h1>
      <div class="mode-tabs">
        <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'ai' }" @click="mode = 'ai'; aiStep = 'input'">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1l1.5 3.5L12 6l-3.5 1.5L7 11l-1.5-3.5L2 6l3.5-1.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>
          AI 智能创建
        </button>
        <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'manual' }" @click="mode = 'manual'">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 4h10M2 7h7M2 10h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
          手动创建
        </button>
        <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'import' }" @click="mode = 'import'">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v7M4 6l3 3 3-3M2 10v1a1 1 0 001 1h8a1 1 0 001-1v-1" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          从文件导入
        </button>
      </div>
    </div>

    <!-- ══ AI 智能创建 ══ -->
    <template v-if="mode === 'ai'">

      <!-- 步骤指示器 -->
      <div class="ai-steps">
        <div class="ai-step" :class="{ 'ai-step--active': aiStep === 'input', 'ai-step--done': aiStep !== 'input' }">
          <span class="ai-step__num">1</span><span class="ai-step__label">输入描述</span>
        </div>
        <div class="ai-step__line"></div>
        <div class="ai-step" :class="{ 'ai-step--active': aiStep === 'edit', 'ai-step--done': aiStep === 'confirm' }">
          <span class="ai-step__num">2</span><span class="ai-step__label">编辑确认</span>
        </div>
        <div class="ai-step__line"></div>
        <div class="ai-step" :class="{ 'ai-step--active': aiStep === 'confirm' }">
          <span class="ai-step__num">3</span><span class="ai-step__label">提交创建</span>
        </div>
      </div>

      <!-- 步骤1：输入 -->
      <div v-if="aiStep === 'input'" class="ai-input-page">
        <div class="ai-input-main">
          <div class="ai-input-toggle">
            <button class="ai-toggle-btn" :class="{ 'ai-toggle-btn--active': aiInputMode === 'text' }" @click="aiInputMode = 'text'">文本输入</button>
            <button class="ai-toggle-btn" :class="{ 'ai-toggle-btn--active': aiInputMode === 'file' }" @click="aiInputMode = 'file'">文件上传</button>
          </div>
          <div v-if="aiInputMode === 'text'">
            <textarea v-model="aiText" class="form-textarea ai-textarea" rows="12"
              placeholder="描述业务场景，AI 将自动提取实体、属性和关系。&#10;&#10;例如：&#10;客户是核心实体，包含姓名、手机号、等级属性。每个客户可有多个订单，订单包含订单号、金额、状态。工程师负责处理工单，工单关联客户和工程师。" />
            <span class="form-hint">{{ aiText.length }} / 8000 字符</span>
          </div>
          <div v-else>
            <div class="file-picker" @click="aiFileRef?.click()">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 4v12M8 8l4-4 4 4M4 18h16" stroke="var(--neutral-400)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <span v-if="aiFile" class="file-name">{{ aiFile.name }}</span>
              <span v-else class="file-placeholder">点击选择文件</span>
              <input ref="aiFileRef" type="file" accept=".txt,.md,.doc,.docx,.pdf" class="file-input-hidden" @change="onAiFileChange" />
            </div>
            <span class="form-hint">支持 txt、md、doc、docx、pdf</span>
          </div>
          <button class="btn-primary btn-extract" @click="handleAiExtract" :disabled="aiExtracting || (!aiText && !aiFile)">
            <svg v-if="aiExtracting" class="spin" width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="rgba(255,255,255,0.4)" stroke-width="1.5"/><path d="M7 2a5 5 0 015 5" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>
            <svg v-else width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1l1.5 3.5L12 6l-3.5 1.5L7 11l-1.5-3.5L2 6l3.5-1.5z" stroke="white" stroke-width="1.2" stroke-linejoin="round"/></svg>
            {{ aiExtracting ? 'AI 提取中...' : 'AI 提取本体' }}
          </button>
        </div>

        <!-- 右侧模板 -->
        <div class="ai-templates">
          <div class="panel-title">场景模板参考</div>
          <div class="tpl-list">
            <div v-for="tpl in templates" :key="tpl.name" class="tpl-card" @click="aiText = tpl.text; aiInputMode = 'text'">
              <div class="tpl-card__head">
                <span class="tpl-card__icon">{{ tpl.icon }}</span>
                <span class="tpl-card__name">{{ tpl.name }}</span>
              </div>
              <p class="tpl-card__desc">{{ tpl.desc }}</p>
              <span class="tpl-card__hint">点击填入</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 步骤2：编辑态 -->
      <div v-if="aiStep === 'edit' && aiResult" class="ai-edit-page">
        <!-- 左：实体列表 -->
        <div class="edit-sidebar">
          <div class="edit-sidebar__head">
            <span class="panel-title" style="margin:0">实体列表</span>
            <button class="btn-sm" @click="addEntity">+ 新增</button>
          </div>
          <div class="entity-list">
            <div
              v-for="(entity, i) in aiResult.entities"
              :key="i"
              class="entity-list-item"
              :class="{ 'entity-list-item--active': selectedEntityIdx === i, 'entity-list-item--unchecked': !entity.selected }"
              @click="selectedEntityIdx = i"
            >
              <label class="entity-check" @click.stop>
                <input type="checkbox" v-model="entity.selected" />
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="1" y="1" width="12" height="12" rx="3" :stroke="entity.selected ? 'var(--semantic-600)' : 'var(--neutral-300)'" stroke-width="1.5" :fill="entity.selected ? 'var(--semantic-600)' : 'none'" />
                  <path v-if="entity.selected" d="M3.5 7l2.5 2.5 4.5-5" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </label>
              <div class="entity-list-item__info">
                <span class="entity-list-item__name">{{ entity.name_cn || entity.name }}</span>
                <span class="entity-list-item__en">{{ entity.name }}</span>
              </div>
              <span class="ai-tier-badge" :style="{ background: tierBg(entity.tier), color: tierFg(entity.tier) }">T{{ entity.tier }}</span>
            </div>
          </div>
          <div class="edit-sidebar__summary">
            已选 {{ aiResult.entities.filter(e=>e.selected).length }} / {{ aiResult.entities.length }} 个实体
          </div>
        </div>

        <!-- 右：编辑面板 -->
        <div class="edit-main">
          <template v-if="selectedEntity">
            <div class="edit-main__head">
              <div class="edit-fields-row">
                <div class="form-row" style="flex:1">
                  <label class="form-label">英文名 <span class="form-required">*</span></label>
                  <input v-model="selectedEntity.name" class="form-input" />
                </div>
                <div class="form-row" style="flex:1">
                  <label class="form-label">中文名 <span class="form-required">*</span></label>
                  <input v-model="selectedEntity.name_cn" class="form-input" />
                </div>
                <div class="form-row">
                  <label class="form-label">层级</label>
                  <div class="tier-selector">
                    <label v-for="t in [1,2,3]" :key="t" class="tier-option" :class="{ 'tier-option--active': selectedEntity.tier === t, [`tier-option--t${t}`]: selectedEntity.tier === t }">
                      <input type="radio" :value="t" v-model="selectedEntity.tier" style="display:none" />
                      <span class="tier-option-label">T{{ t }}</span>
                    </label>
                  </div>
                </div>
              </div>
              <div class="form-row">
                <label class="form-label">描述</label>
                <input v-model="selectedEntity.description" class="form-input" placeholder="业务含义描述" />
              </div>
            </div>

            <!-- 属性编辑 -->
            <div class="edit-section">
              <div class="edit-section__head">
                <span class="panel-subtitle">属性</span>
                <button class="btn-sm" @click="addAttrToSelected">+ 添加属性</button>
              </div>
              <div v-if="selectedEntity.attributes.length" class="attrs-table">
                <div class="attr-row attr-row--header">
                  <span>属性名</span><span>类型</span><span>描述</span><span>必填</span><span></span>
                </div>
                <div v-for="(attr, ai) in selectedEntity.attributes" :key="ai" class="attr-row">
                  <input v-model="attr.name" class="form-input form-input--sm" placeholder="attr_name" />
                  <select v-model="attr.type" class="form-input form-input--sm">
                    <option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</option>
                  </select>
                  <input v-model="attr.description" class="form-input form-input--sm" placeholder="说明" />
                  <input type="checkbox" v-model="attr.required" />
                  <button class="btn-icon-del" @click="selectedEntity.attributes.splice(ai,1)">×</button>
                </div>
              </div>
              <div v-else class="attrs-empty text-caption">暂无属性</div>
            </div>
          </template>
          <div v-else class="edit-empty">
            <p class="text-caption">从左侧选择一个实体进行编辑</p>
          </div>

          <!-- 关系编辑（底部） -->
          <div class="edit-section edit-section--relations">
            <div class="edit-section__head">
              <span class="panel-subtitle">关系列表</span>
              <button class="btn-sm" @click="addRelation">+ 添加关系</button>
            </div>
            <div v-if="aiResult.relations.length" class="rel-table">
              <div class="rel-row rel-row--header">
                <span>源实体</span><span>目标实体</span><span>关系名</span><span>类型</span><span>基数</span><span></span>
              </div>
              <div v-for="(rel, ri) in aiResult.relations" :key="ri" class="rel-row">
                <input v-model="rel.from_entity" class="form-input form-input--sm" />
                <input v-model="rel.to_entity" class="form-input form-input--sm" />
                <input v-model="rel.name" class="form-input form-input--sm" />
                <select v-model="rel.rel_type" class="form-input form-input--sm">
                  <option v-for="rt in relTypes" :key="rt" :value="rt">{{ rt }}</option>
                </select>
                <select v-model="rel.cardinality" class="form-input form-input--sm">
                  <option v-for="c in cardinalities" :key="c" :value="c">{{ c }}</option>
                </select>
                <button class="btn-icon-del" @click="aiResult.relations.splice(ri,1)">×</button>
              </div>
            </div>
            <div v-else class="attrs-empty text-caption">暂无关系</div>
          </div>

          <div class="edit-actions">
            <button class="btn-secondary" @click="aiStep = 'input'">← 重新提取</button>
            <button class="btn-primary" @click="aiStep = 'confirm'" :disabled="aiResult.entities.filter(e=>e.selected).length === 0">下一步：确认提交 →</button>
          </div>
        </div>
      </div>

      <!-- 步骤3：确认提交 -->
      <div v-if="aiStep === 'confirm' && aiResult" class="ai-confirm-page">
        <div class="confirm-summary">
          <div class="confirm-summary__title">即将创建以下本体对象</div>
          <div class="confirm-stats">
            <span class="ai-tag ai-tag--blue">{{ aiResult.entities.filter(e=>e.selected).length }} 个实体</span>
            <span class="ai-tag ai-tag--green">{{ selectedTotalAttrs }} 个属性</span>
            <span class="ai-tag ai-tag--amber">{{ selectedRelations.length }} 个关系</span>
          </div>
        </div>

        <div class="confirm-list">
          <div v-for="(entity, i) in aiResult.entities.filter(e=>e.selected)" :key="i" class="confirm-entity">
            <div class="confirm-entity__head">
              <span class="ai-tier-badge" :style="{ background: tierBg(entity.tier), color: tierFg(entity.tier) }">T{{ entity.tier }}</span>
              <span class="confirm-entity__name">{{ entity.name_cn }}</span>
              <span class="confirm-entity__en">{{ entity.name }}</span>
              <span class="confirm-entity__attrs">{{ entity.attributes.length }} 个属性</span>
            </div>
            <div v-if="entity.description" class="confirm-entity__desc">{{ entity.description }}</div>
          </div>
        </div>

        <div v-if="selectedRelations.length" class="confirm-relations">
          <div class="panel-subtitle" style="margin-bottom:8px">关系</div>
          <div v-for="(rel, i) in selectedRelations" :key="i" class="confirm-rel-row">
            <span>{{ rel.from_entity }}</span>
            <span class="confirm-rel-arrow">—{{ rel.rel_type }}→</span>
            <span>{{ rel.to_entity }}</span>
            <span class="confirm-rel-card">{{ rel.cardinality }}</span>
          </div>
        </div>

        <div class="confirm-actions">
          <button class="btn-secondary" @click="aiStep = 'edit'">← 返回编辑</button>
          <button class="btn-primary" @click="handleAiCreate" :disabled="aiCreating">
            <svg v-if="aiCreating" class="spin" width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="rgba(255,255,255,0.4)" stroke-width="1.5"/><path d="M7 2a5 5 0 015 5" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>
            {{ aiCreating ? '创建中...' : '确认创建' }}
          </button>
        </div>
      </div>
    </template>

    <!-- 手动创建 -->
    <div v-if="mode === 'manual'" class="single-panel">
      <form @submit.prevent="handleSubmit" class="entity-form">
        <div class="form-grid">
          <div class="form-row">
            <label class="form-label">对象名称 (英文) <span class="form-required">*</span></label>
            <input v-model="form.name" class="form-input" placeholder="如 Customer, FTTRSubscription" required />
          </div>
          <div class="form-row">
            <label class="form-label">中文名称 <span class="form-required">*</span></label>
            <input v-model="form.name_cn" class="form-input" placeholder="如 客户, FTTR订阅" required />
          </div>
          <div class="form-row">
            <label class="form-label">层级</label>
            <div class="tier-selector">
              <label v-for="t in [1,2,3]" :key="t" class="tier-option" :class="{ 'tier-option--active': form.tier === t }">
                <input type="radio" :value="t" v-model="form.tier" style="display:none" />
                <span class="tier-option-label">T{{ t }}</span>
                <span class="tier-option-name">{{ { 1:'核心', 2:'领域', 3:'场景' }[t] }}</span>
              </label>
            </div>
          </div>
          <div class="form-row form-row--full">
            <label class="form-label">描述</label>
            <textarea v-model="form.description" class="form-textarea" rows="3" placeholder="描述该对象的业务含义" />
          </div>
        </div>
        <div class="attrs-section">
          <div class="attrs-header">
            <span class="panel-subtitle">属性列表</span>
            <button type="button" class="btn-sm" @click="addAttr">+ 添加属性</button>
          </div>
          <div v-if="form.attributes.length" class="attrs-table">
            <div class="attr-row attr-row--header"><span>属性名</span><span>类型</span><span>描述</span><span>必填</span><span></span></div>
            <div v-for="(attr, i) in form.attributes" :key="i" class="attr-row">
              <input v-model="attr.name" class="form-input form-input--sm" placeholder="attr_name" />
              <select v-model="attr.type" class="form-input form-input--sm">
                <option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</option>
              </select>
              <input v-model="attr.description" class="form-input form-input--sm" placeholder="说明" />
              <input type="checkbox" v-model="attr.required" />
              <button type="button" class="btn-icon-del" @click="form.attributes.splice(i,1)">×</button>
            </div>
          </div>
          <div v-else class="attrs-empty text-caption">暂无属性，点击「添加属性」</div>
        </div>
        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.back()">取消</button>
          <button type="submit" class="btn-primary" :disabled="submitting">{{ submitting ? '创建中...' : '创建对象' }}</button>
        </div>
      </form>
    </div>

    <!-- 从文件导入 -->
    <div v-if="mode === 'import'" class="single-panel">
      <div class="entity-form">
        <!-- 模板下载 -->
        <div class="tpl-download">
          <div class="tpl-download__info">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1v9M5 7l3 3 3-3M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" stroke="var(--status-info)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span>下载 JSON 模板参考（宽带退单稽核场景 V1.1 规范）</span>
          </div>
          <a href="/ontology_template.json" download="ontology_template.json" class="btn-sm">下载模板</a>
        </div>

        <!-- 格式说明 -->
        <div class="schema-hint">
          <div class="schema-hint__title">JSON 文件结构说明</div>
          <div class="schema-hint__fields">
            <div class="schema-field"><code>scenario</code><span>场景元数据（名称、命名空间、描述）</span></div>
            <div class="schema-field"><code>object_types</code><span>实体定义列表，含 tier、properties、datasource_ref</span></div>
            <div class="schema-field"><code>link_types</code><span>关系定义列表，含 source_type、target_type、cardinality</span></div>
            <div class="schema-field"><code>action_types</code><span>动作定义列表，含 trigger、parameters、effects</span></div>
            <div class="schema-field"><code>business_rules</code><span>业务规则列表，含 conditions、applicable_objects</span></div>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label">文件格式</label>
          <div class="format-selector">
            <label v-for="f in ['json','owl','ttl']" :key="f" class="format-option" :class="{ 'format-option--active': fileFormat === f }">
              <input type="radio" :value="f" v-model="fileFormat" style="display:none" />{{ f.toUpperCase() }}
            </label>
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">命名空间前缀</label>
          <input v-model="fileNamespace" class="form-input" placeholder="如 telecom:" />
        </div>
        <div class="form-row">
          <label class="form-label">选择文件</label>
          <div class="file-picker" @click="fileInputRef?.click()">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 4v12M8 8l4-4 4 4M4 18h16" stroke="var(--neutral-400)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
            <span v-else class="file-placeholder">点击选择文件</span>
            <input ref="fileInputRef" type="file" :accept="fileAccept" class="file-input-hidden" @change="onFileChange" />
          </div>
        </div>
        <div v-if="jsonPreview" class="import-preview">
          <div class="import-preview__title">文件预览</div>
          <div class="import-preview__stats">
            <span>场景：{{ jsonPreview.scenario }}</span>
            <span>{{ jsonPreview.objectCount }} 个对象</span>
            <span>{{ jsonPreview.linkCount }} 个关系</span>
            <span>{{ jsonPreview.actionCount }} 个动作</span>
            <span>{{ jsonPreview.ruleCount }} 个规则</span>
          </div>
        </div>
        <div v-if="importResult" class="import-result">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="var(--status-success-bg)"/><path d="M5 8l2 2 4-4" stroke="var(--status-success)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          导入完成：{{ importResult.entities_created }} 个实体，{{ importResult.relations_created }} 个关系
        </div>
        <div class="form-actions">
          <button class="btn-secondary" @click="router.back()">取消</button>
          <button class="btn-primary" @click="handleFileImport" :disabled="submitting || !selectedFile">{{ submitting ? '导入中...' : '导入文件' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import OntologyBreadcrumb from '../../components/common/OntologyBreadcrumb.vue'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import { post } from '../../api/client'
import { useToast } from '../../composables/useToast'
import type { FileImportResult } from '../../types'

const router = useRouter()
const toast = useToast()

const breadcrumbs = [
  { label: '本体管理', path: '/ontology' },
  { label: '本体目录', path: '/browser' },
  { label: '新建本体对象' },
]

const mode = ref<'ai' | 'manual' | 'import'>('ai')
const attrTypes = ['string', 'number', 'boolean', 'date', 'ref', 'computed', 'enum', 'json']
const relTypes = ['has', 'belongs_to', 'references', 'triggers', 'produces', 'consumes']
const cardinalities = ['1:1', '1:N', 'N:1', 'N:N']
const submitting = ref(false)

const tierColors: Record<number, { bg: string; fg: string }> = {
  1: { bg: 'var(--tier1-bg)', fg: 'var(--tier1-text)' },
  2: { bg: 'var(--tier2-bg)', fg: 'var(--tier2-text)' },
  3: { bg: 'var(--tier3-bg)', fg: 'var(--tier3-text)' },
}
const tierBg = (t: number) => tierColors[t]?.bg ?? '#eee'
const tierFg = (t: number) => tierColors[t]?.fg ?? '#333'

// ── 场景模板 ──
const templates = [
  {
    icon: '📡',
    name: '宽带退单稽核',
    desc: '宽带装机退单根因分析，涉及客户、工程师、工单、质检等实体',
    text: `宽带退单稽核场景涉及以下核心实体：
客户（Customer）是核心对象，包含客户ID、姓名、手机号、地址、套餐等级属性。
宽带退单工单（BroadbandChurnOrder）记录退单信息，包含工单ID、退单时间、退单原因、状态、根因类别属性，关联客户和工程师。
工程师（Engineer）负责装机施工，包含工号、姓名、技能等级、所属团队属性。
语音质检记录（VoiceAuditRecord）记录客服通话质检结果，包含录音ID、质检得分、关键词、情绪标签属性，关联工单。
施工记录（ConstructionRecord）记录现场施工情况，包含施工时间、施工结果、异常描述属性，关联工单和工程师。
稽核规则（AuditRule）定义归因判断逻辑，包含规则ID、规则名称、触发条件、归因类别属性。`,
  },
  {
    icon: '📱',
    name: '携号转网预警',
    desc: '识别高风险携转用户，输出预警等级和挽留策略',
    text: `携号转网预警场景涉及以下核心实体：
用户（User）是核心对象，包含用户ID、手机号、在网时长、套餐类型、ARPU值属性。
套餐（Package）描述用户订购的产品，包含套餐ID、套餐名称、月租费、流量额度、语音分钟数属性。
投诉记录（ComplaintRecord）记录用户投诉历史，包含投诉ID、投诉时间、投诉类型、处理状态属性，关联用户。
携转查询记录（MnpQueryRecord）记录用户查询携转的行为，包含查询时间、查询渠道属性，关联用户。
预警结果（AlertResult）输出风险评估结论，包含风险等级、风险原因、挽留策略、置信度属性，关联用户。`,
  },
  {
    icon: '🏢',
    name: '政企根因分析',
    desc: '政企客户网络故障多维根因分析',
    text: `政企根因分析场景涉及以下核心实体：
政企客户（EnterpriseCustomer）是核心对象，包含客户ID、企业名称、行业类型、合同等级、专属客户经理属性。
网络设备（NetworkDevice）描述客户侧和运营商侧设备，包含设备ID、设备类型、IP地址、所属网络层级属性。
故障工单（FaultOrder）记录故障处理过程，包含工单ID、故障时间、故障描述、影响范围、处理状态属性，关联政企客户。
根因分析结果（RootCauseResult）输出分析结论，包含主因类别、次因类别、故障链路描述、修复建议属性，关联故障工单。`,
  },
]

// ── 手动创建 ──
const form = reactive({
  name: '', name_cn: '', tier: 1, description: '',
  attributes: [] as { name: string; type: string; description: string; required: boolean }[],
})
function addAttr() { form.attributes.push({ name: '', type: 'string', description: '', required: false }) }
async function handleSubmit() {
  if (!form.name || !form.name_cn) return
  submitting.value = true
  try {
    await entityApi.create({ name: form.name, name_cn: form.name_cn, tier: form.tier, description: form.description, attributes: form.attributes.filter(a => a.name) } as never)
    toast.success('对象创建成功')
    router.push('/browser')
  } catch (e) { toast.error(`创建失败: ${(e as Error).message}`) }
  finally { submitting.value = false }
}

// ── 文件导入 ──
const fileFormat = ref<'json' | 'owl' | 'ttl'>('json')
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const fileNamespace = ref('')
const jsonPreview = ref<{ scenario: string; objectCount: number; linkCount: number; actionCount: number; ruleCount: number } | null>(null)
const importResult = ref<FileImportResult | null>(null)
const fileAccept = computed(() => ({ json: '.json', owl: '.owl,.rdf,.xml', ttl: '.ttl' }[fileFormat.value]))

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] || null
  selectedFile.value = file; jsonPreview.value = null; importResult.value = null
  if (file && fileFormat.value === 'json') {
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result as string)
        const scenario = data.scenario
        jsonPreview.value = { scenario: scenario?.scenario_name || scenario?.scenario_short_name || '未知', objectCount: data.object_types?.length || 0, linkCount: data.link_types?.length || 0, actionCount: data.action_types?.length || 0, ruleCount: data.business_rules?.length || 0 }
        if (scenario?.namespace && !fileNamespace.value) fileNamespace.value = scenario.namespace
      } catch { jsonPreview.value = null }
    }
    reader.readAsText(file)
  }
}
async function handleFileImport() {
  if (!selectedFile.value) return
  submitting.value = true; importResult.value = null
  try {
    const res = await entityApi.importFromFile(selectedFile.value, fileFormat.value, fileNamespace.value || undefined)
    importResult.value = res
    toast.success(`导入完成：创建 ${res.entities_created} 个实体，${res.relations_created} 个关系`)
  } catch (e) { toast.error(`导入失败: ${(e as Error).message}`) }
  finally { submitting.value = false }
}

// ── AI 智能创建 ──
interface AiAttr { name: string; type: string; description: string; required: boolean }
interface AiEntity { name: string; name_cn: string; tier: number; description: string; attributes: AiAttr[]; selected: boolean }
interface AiRelation { from_entity: string; to_entity: string; name: string; rel_type: string; cardinality: string }
interface AiResult { entities: AiEntity[]; relations: AiRelation[] }

const aiStep = ref<'input' | 'edit' | 'confirm'>('input')
const aiInputMode = ref<'text' | 'file'>('text')
const aiText = ref('')
const aiFile = ref<File | null>(null)
const aiFileRef = ref<HTMLInputElement | null>(null)
const aiExtracting = ref(false)
const aiCreating = ref(false)
const aiResult = ref<AiResult | null>(null)
const selectedEntityIdx = ref(0)

const selectedEntity = computed(() => aiResult.value?.entities[selectedEntityIdx.value] ?? null)
const selectedTotalAttrs = computed(() => aiResult.value?.entities.filter(e => e.selected).reduce((s, e) => s + e.attributes.length, 0) ?? 0)
const selectedRelations = computed(() => {
  if (!aiResult.value) return []
  const names = new Set(aiResult.value.entities.filter(e => e.selected).map(e => e.name))
  return aiResult.value.relations.filter(r => names.has(r.from_entity) || names.has(r.to_entity))
})

function onAiFileChange(e: Event) { aiFile.value = (e.target as HTMLInputElement).files?.[0] || null }

function addEntity() {
  if (!aiResult.value) return
  aiResult.value.entities.push({ name: 'NewEntity', name_cn: '新实体', tier: 2, description: '', attributes: [], selected: true })
  selectedEntityIdx.value = aiResult.value.entities.length - 1
}

function addAttrToSelected() {
  selectedEntity.value?.attributes.push({ name: '', type: 'string', description: '', required: false })
}

function addRelation() {
  aiResult.value?.relations.push({ from_entity: '', to_entity: '', name: '', rel_type: 'has', cardinality: '1:N' })
}

async function handleAiExtract() {
  aiExtracting.value = true
  try {
    let data: AiResult
    if (aiInputMode.value === 'text') {
      const fd = new FormData(); fd.append('text', aiText.value)
      data = await post<AiResult>('/entities/ai-extract', fd, { timeout: 60000 })
    } else {
      if (!aiFile.value) { toast.error('请选择文件'); return }
      const fd = new FormData(); fd.append('file', aiFile.value)
      data = await post<AiResult>('/entities/ai-extract', fd, { timeout: 60000 })
    }
    data.entities.forEach(e => {
      e.selected = true
      e.attributes = (e.attributes || []).map(a => ({ ...a, required: false }))
    })
    aiResult.value = data
    selectedEntityIdx.value = 0
    aiStep.value = 'edit'
    toast.success(`AI 提取完成：${data.entities.length} 个实体`)
  } catch (e) { toast.error(`提取失败: ${(e as Error).message}`) }
  finally { aiExtracting.value = false }
}

async function handleAiCreate() {
  if (!aiResult.value) return
  aiCreating.value = true
  try {
    const selected = aiResult.value.entities.filter(e => e.selected)
    const created: Record<string, string> = {}
    for (const entity of selected) {
      const res = await entityApi.create({ name: entity.name, name_cn: entity.name_cn, tier: entity.tier as any, description: entity.description, attributes: entity.attributes.map(a => ({ id: '', name: a.name, type: a.type as any, description: a.description, required: a.required })) } as any)
      created[entity.name] = res.id
    }
    for (const rel of selectedRelations.value) {
      const fromId = created[rel.from_entity], toId = created[rel.to_entity]
      if (fromId && toId) await relationApi.create({ from_entity_id: fromId, to_entity_id: toId, name: rel.name, rel_type: rel.rel_type, cardinality: rel.cardinality })
    }
    toast.success(`成功创建 ${Object.keys(created).length} 个本体对象`)
    router.push('/browser')
  } catch (e) { toast.error(`创建失败: ${(e as Error).message}`) }
  finally { aiCreating.value = false }
}
</script>

<style scoped>
.create-page { padding: 24px; max-width: 1400px; }
.create-page__header { display: flex; align-items: center; justify-content: space-between; margin: 16px 0 24px; flex-wrap: wrap; gap: 12px; }
.create-page__title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }

.mode-tabs { display: flex; gap: 4px; background: var(--neutral-100); padding: 4px; border-radius: var(--radius-lg); }
.mode-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: var(--radius-md); border: none; background: transparent; font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-600); cursor: pointer; transition: all var(--transition-fast); }
.mode-tab:hover { color: var(--neutral-800); }
.mode-tab--active { background: var(--neutral-0); color: var(--semantic-600); box-shadow: 0 1px 4px rgba(0,0,0,0.08); }

/* 步骤指示器 */
.ai-steps { display: flex; align-items: center; margin-bottom: 24px; }
.ai-step { display: flex; align-items: center; gap: 8px; }
.ai-step__num { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; background: var(--neutral-200); color: var(--neutral-500); transition: all var(--transition-fast); }
.ai-step__label { font-size: var(--text-body-size); color: var(--neutral-500); font-weight: 500; }
.ai-step--active .ai-step__num { background: var(--semantic-600); color: #fff; }
.ai-step--active .ai-step__label { color: var(--semantic-700); }
.ai-step--done .ai-step__num { background: var(--status-success); color: #fff; }
.ai-step--done .ai-step__label { color: var(--neutral-700); }
.ai-step__line { flex: 1; height: 2px; background: var(--neutral-200); margin: 0 12px; max-width: 80px; }

/* 步骤1：输入页 */
.ai-input-page { display: grid; grid-template-columns: 1fr 320px; gap: 20px; align-items: start; }
.ai-input-main { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.ai-textarea { width: 100%; box-sizing: border-box; }
.ai-input-toggle { display: flex; gap: 4px; }
.ai-toggle-btn { padding: 5px 14px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: transparent; font-size: var(--text-caption-size); color: var(--neutral-600); cursor: pointer; transition: all var(--transition-fast); }
.ai-toggle-btn--active { background: var(--semantic-50); border-color: var(--semantic-300); color: var(--semantic-700); }
.btn-extract { width: 100%; justify-content: center; display: flex; align-items: center; gap: 6px; padding: 10px; }

/* 模板 */
.ai-templates { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 16px; }
.tpl-list { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.tpl-card { padding: 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: all var(--transition-fast); }
.tpl-card:hover { border-color: var(--semantic-300); background: var(--semantic-50); }
.tpl-card__head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.tpl-card__icon { font-size: 16px; }
.tpl-card__name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.tpl-card__desc { font-size: var(--text-caption-size); color: var(--neutral-500); margin: 0 0 6px; line-height: 1.4; }
.tpl-card__hint { font-size: 11px; color: var(--semantic-500); }

/* 步骤2：编辑页 */
.ai-edit-page { display: grid; grid-template-columns: 260px 1fr; gap: 16px; align-items: start; }
.edit-sidebar { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.edit-sidebar__head { display: flex; align-items: center; justify-content: space-between; }
.entity-list { display: flex; flex-direction: column; gap: 4px; }
.entity-list-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: var(--radius-md); cursor: pointer; transition: background var(--transition-fast); border: 1px solid transparent; }
.entity-list-item:hover { background: var(--neutral-50); }
.entity-list-item--active { background: var(--semantic-50); border-color: var(--semantic-200); }
.entity-list-item--unchecked { opacity: 0.5; }
.entity-check { cursor: pointer; display: flex; align-items: center; flex-shrink: 0; }
.entity-check input { display: none; }
.entity-list-item__info { flex: 1; min-width: 0; }
.entity-list-item__name { display: block; font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-800); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.entity-list-item__en { display: block; font-size: 11px; color: var(--neutral-400); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.edit-sidebar__summary { font-size: var(--text-caption-size); color: var(--neutral-500); padding-top: 8px; border-top: 1px solid var(--neutral-100); }

.edit-main { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.edit-main__head { display: flex; flex-direction: column; gap: 10px; padding-bottom: 16px; border-bottom: 1px solid var(--neutral-100); }
.edit-fields-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.edit-empty { display: flex; align-items: center; justify-content: center; padding: 40px; color: var(--neutral-400); }
.edit-section { display: flex; flex-direction: column; gap: 8px; }
.edit-section--relations { padding-top: 16px; border-top: 1px solid var(--neutral-100); }
.edit-section__head { display: flex; align-items: center; justify-content: space-between; }
.edit-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 16px; border-top: 1px solid var(--neutral-100); }

/* 关系表格 */
.rel-table { display: flex; flex-direction: column; gap: 4px; }
.rel-row { display: grid; grid-template-columns: 1fr 1fr 1fr 90px 70px 28px; gap: 6px; align-items: center; }
.rel-row--header { font-size: var(--text-caption-size); font-weight: 500; color: var(--neutral-500); padding: 0 2px; }

/* 步骤3：确认页 */
.ai-confirm-page { max-width: 800px; display: flex; flex-direction: column; gap: 20px; }
.confirm-summary { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 20px; }
.confirm-summary__title { font-size: 15px; font-weight: 600; color: var(--neutral-800); margin-bottom: 12px; }
.confirm-stats { display: flex; gap: 8px; }
.confirm-list { display: flex; flex-direction: column; gap: 8px; }
.confirm-entity { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); padding: 12px 16px; }
.confirm-entity__head { display: flex; align-items: center; gap: 10px; }
.confirm-entity__name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.confirm-entity__en { font-size: var(--text-caption-size); color: var(--neutral-400); }
.confirm-entity__attrs { font-size: var(--text-caption-size); color: var(--neutral-500); margin-left: auto; }
.confirm-entity__desc { font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 6px; }
.confirm-relations { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 16px; }
.confirm-rel-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--neutral-50); font-size: var(--text-body-size); color: var(--neutral-700); }
.confirm-rel-arrow { color: var(--semantic-500); font-size: var(--text-caption-size); font-weight: 500; }
.confirm-rel-card { margin-left: auto; font-size: var(--text-caption-size); color: var(--neutral-400); }
.confirm-actions { display: flex; justify-content: flex-end; gap: 8px; }

/* 通用 */
.form-row { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-700); }
.form-required { color: var(--status-error); }
.form-input { padding: 7px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); outline: none; transition: border-color var(--transition-fast); }
.form-input:focus { border-color: var(--semantic-400); }
.form-input--sm { padding: 4px 8px; font-size: var(--text-caption-size); }
.form-textarea { padding: 8px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); resize: vertical; outline: none; font-family: inherit; transition: border-color var(--transition-fast); }
.form-textarea:focus { border-color: var(--semantic-400); }
.form-hint { font-size: var(--text-caption-size); color: var(--neutral-400); }
.panel-title { font-size: 14px; font-weight: 600; color: var(--neutral-800); margin-bottom: 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.panel-subtitle { font-size: 13px; font-weight: 600; color: var(--neutral-700); }

.file-picker { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 24px; border: 2px dashed var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: border-color var(--transition-fast); }
.file-picker:hover { border-color: var(--semantic-300); }
.file-input-hidden { display: none; }
.file-name { font-size: var(--text-body-size); color: var(--semantic-600); font-weight: 500; }
.file-placeholder { font-size: var(--text-body-size); color: var(--neutral-400); }

.ai-tier-badge { padding: 1px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.3px; flex-shrink: 0; }
.ai-tag { display: inline-block; padding: 1px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.ai-tag--blue { background: var(--status-info-bg); color: var(--status-info); }
.ai-tag--green { background: var(--status-success-bg); color: var(--status-success); }
.ai-tag--amber { background: var(--status-warning-bg); color: var(--kinetic-700); }

.tier-selector { display: flex; gap: 8px; }
.tier-option { display: flex; flex-direction: column; align-items: center; padding: 6px 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: all var(--transition-fast); gap: 1px; }
.tier-option:hover { border-color: var(--neutral-400); }
.tier-option--active { border-color: var(--semantic-400); background: var(--semantic-50); }
.tier-option-label { font-size: 13px; font-weight: 700; color: var(--neutral-700); }
.tier-option-name { font-size: 10px; color: var(--neutral-500); }

.attrs-section { margin-bottom: 4px; }
.attrs-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.attrs-table { display: flex; flex-direction: column; gap: 4px; }
.attr-row { display: grid; grid-template-columns: 1.2fr 90px 1.5fr 40px 28px; gap: 6px; align-items: center; }
.attr-row--header { font-size: var(--text-caption-size); font-weight: 500; color: var(--neutral-500); padding: 0 2px; }
.attrs-empty { color: var(--neutral-400); padding: 8px 0; }
.btn-icon-del { width: 24px; height: 24px; border: none; background: transparent; color: var(--neutral-400); cursor: pointer; font-size: 16px; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; }
.btn-icon-del:hover { background: var(--status-error-bg); color: var(--status-error); }

.single-panel { max-width: 700px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 24px; }
.entity-form { display: flex; flex-direction: column; gap: 16px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 20px; }
.form-row--full { grid-column: 1 / -1; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 16px; border-top: 1px solid var(--neutral-100); }

.format-selector { display: flex; gap: 8px; }
.format-option { padding: 5px 16px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-600); transition: all var(--transition-fast); }
.format-option--active { border-color: var(--semantic-400); background: var(--semantic-50); color: var(--semantic-700); }
.import-preview { background: var(--neutral-50); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); padding: 12px 14px; }
.import-preview__title { font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-600); margin-bottom: 6px; }
.import-preview__stats { display: flex; gap: 16px; flex-wrap: wrap; font-size: var(--text-caption-size); color: var(--neutral-700); }
.import-result { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: var(--status-success-bg); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--status-success); }

.tpl-download { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: var(--status-info-bg); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); }
.tpl-download__info { display: flex; align-items: center; gap: 8px; font-size: var(--text-body-size); color: var(--status-info); }

.schema-hint { background: var(--neutral-50); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); padding: 12px 14px; }
.schema-hint__title { font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-600); margin-bottom: 8px; }
.schema-hint__fields { display: flex; flex-direction: column; gap: 4px; }
.schema-field { display: flex; align-items: baseline; gap: 10px; font-size: var(--text-caption-size); }
.schema-field code { font-family: var(--font-mono); color: var(--semantic-600); background: var(--neutral-0); padding: 1px 6px; border-radius: 3px; border: 1px solid var(--neutral-200); min-width: 130px; }
.schema-field span { color: var(--neutral-500); }

.btn-primary { padding: 8px 20px; border-radius: var(--radius-md); border: none; background: var(--semantic-600); color: #fff; font-size: var(--text-body-size); font-weight: 500; cursor: pointer; transition: background var(--transition-fast); display: inline-flex; align-items: center; gap: 6px; }
.btn-primary:hover:not(:disabled) { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 8px 20px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); font-size: var(--text-body-size); font-weight: 500; cursor: pointer; transition: all var(--transition-fast); }
.btn-secondary:hover { border-color: var(--neutral-400); }
.btn-sm { padding: 4px 12px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-600); font-size: var(--text-caption-size); cursor: pointer; transition: all var(--transition-fast); }
.btn-sm:hover { border-color: var(--neutral-400); color: var(--neutral-800); }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>