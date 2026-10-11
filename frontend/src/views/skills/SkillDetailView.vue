<template>
  <div class="skill-detail" :class="{ 'skill-detail--readonly': saved && !canManage }">
    <a-spin v-if="loading" class="detail-loading" tip="正在加载技能…" />
    <a-result
      v-else-if="!route.params.id && !roleCanEdit"
      status="403"
      title="当前账户仅可查看业务技能"
      sub-title="创建、编辑和发布技能需要编辑者或管理员权限。"
      ><template #extra
        ><a-button @click="router.push('/skills')">返回技能中心</a-button></template
      ></a-result
    >
    <a-result v-else-if="loadError" status="error" title="无法加载技能" :sub-title="loadError"
      ><template #extra
        ><a-button @click="load">重试</a-button
        ><a-button @click="router.push('/skills')">返回技能中心</a-button></template
      ></a-result
    >
    <template v-else>
      <header class="detail-header">
        <div>
          <button class="back-link" @click="router.push('/skills')">‹ 业务技能</button>
          <div class="detail-title">
            <h1>{{ form.name || '新建业务技能' }}</h1>
            <a-tag :color="form.status === 'active' ? 'green' : 'blue'">{{ statusLabel }}</a-tag
            ><a-tag v-if="saved?.current_version">在线 v{{ saved.current_version }}</a-tag>
          </div>
          <p>
            {{ dirty ? '有未保存修改' : saved ? '草稿已保存' : '填写业务说明，保存后即可测试与发布'
            }}<span v-if="saved?.has_changes && saved.current_version"> · 草稿修改待发布</span>
          </p>
        </div>
        <a-space wrap
          ><a-button
            v-if="saved && canManage"
            @click="toggleArchive"
            :loading="archiving"
            :disabled="saving || testing || publishing || validating"
            >{{ saved.status === 'archived' ? '恢复技能' : '归档' }}</a-button
          ><a-button
            v-if="canEditContent"
            @click="save"
            :loading="saving"
            :disabled="testing || publishing || validating"
            >保存草稿</a-button
          ><a-button
            v-if="canEditContent"
            type="primary"
            @click="preparePublish"
            :loading="publishing"
            :disabled="
              saving ||
              testing ||
              validating ||
              !saved ||
              (!dirty && !saved.has_changes && !!saved.current_version)
            "
            >发布新版本</a-button
          ></a-space
        >
      </header>
      <a-alert
        v-if="saved && !canManage"
        type="info"
        show-icon
        message="当前技能为只读，可查看说明、依赖与历史记录。编辑、测试和发布需要创建者或管理员权限。"
        class="detail-banner"
      />
      <a-alert
        v-if="saved?.current_version && canEditContent"
        type="info"
        show-icon
        message="当前编辑的是草稿。保存不会改变已发布版本；智能体继续使用挂载时的固定版本。"
        class="detail-banner"
      />
      <a-alert
        v-if="saved?.status === 'archived'"
        type="warning"
        show-icon
        message="此技能已归档。已有引用保留，恢复后可继续编辑和发布。"
        class="detail-banner"
      />
      <a-alert
        v-if="formError"
        :message="formError"
        type="error"
        show-icon
        closable
        @close="formError = ''"
        class="detail-banner"
      />
      <div class="detail-workspace">
        <section class="detail-main">
          <a-tabs v-model:active-key="tab" class="detail-tabs">
            <a-tab-pane key="instructions" tab="技能说明">
              <a-form layout="vertical" :disabled="!editable">
                <div class="form-grid">
                  <a-form-item label="技能名称" required
                    ><a-input
                      v-model:value="form.name"
                      :maxlength="100"
                      placeholder="例如：设备故障诊断" /></a-form-item
                  ><a-form-item label="负责团队"
                    ><a-input v-model:value="form.owner_team" placeholder="例如：设备运维团队"
                  /></a-form-item>
                </div>
                <a-form-item label="业务用途"
                  ><a-textarea
                    v-model:value="form.description"
                    :rows="2"
                    :maxlength="2000"
                    placeholder="说明技能解决什么业务问题，以及预期价值"
                /></a-form-item>
                <a-form-item label="操作指引" required
                  ><a-textarea
                    v-model:value="form.prompt_template"
                    :rows="13"
                    placeholder="写清执行步骤、判断依据、信息不足时的处理方式，以及结果表达要求。可引用下方绑定的对象、函数和行动。"
                  />
                  <p class="field-help">
                    建议按“收集信息 → 检查与判断 → 提出建议 →
                    输出依据”编写，让同一业务方法能够被重复使用。
                  </p></a-form-item
                >
                <div class="form-grid">
                  <a-form-item label="适用任务"
                    ><a-textarea
                      v-model:value="form.applicable_tasks"
                      :rows="3"
                      placeholder="列出适用业务任务与触发条件" /></a-form-item
                  ><a-form-item label="不适用任务"
                    ><a-textarea
                      v-model:value="form.excluded_tasks"
                      :rows="3"
                      placeholder="说明边界条件与应转交人工的情况"
                  /></a-form-item>
                </div>
                <div class="form-grid">
                  <a-form-item label="可见范围"
                    ><a-select
                      v-model:value="form.visibility"
                      :options="[
                        { value: 'private', label: '仅创建者可见' },
                        { value: 'workspace', label: '工作空间共享' },
                      ]" /></a-form-item
                  ><a-form-item label="业务标签"
                    ><a-select
                      v-model:value="form.tags"
                      mode="tags"
                      placeholder="输入标签后按回车添加"
                  /></a-form-item>
                </div>
              </a-form>
            </a-tab-pane>
            <a-tab-pane key="dependencies" tab="本体与工具">
              <a-form layout="vertical" :disabled="!editable">
                <div class="form-grid">
                  <a-form-item label="关联本体" required
                    ><a-select
                      :value="form.ontology_id || undefined"
                      allow-clear
                      :options="ontologyOptions"
                      placeholder="选择技能使用的业务本体"
                      @update:value="changeOntology" /></a-form-item
                  ><a-form-item label="本体发布版本" required
                    ><a-select
                      :value="form.ontology_version_id || undefined"
                      :disabled="!editable || !form.ontology_id"
                      :options="versionOptions"
                      placeholder="固定引用已发布版本"
                      @update:value="changeOntologyVersion"
                  /></a-form-item>
                </div>
                <a-alert
                  v-if="form.ontology_id && !versionOptions.length && !catalogLoading"
                  type="warning"
                  message="该本体还没有发布版本。请先到本体发布页发布，再刷新依赖。"
                  show-icon
                  class="section-alert"
                  ><template #action
                    ><a-button size="small" @click="router.push('/ontology/publish')"
                      >本体发布</a-button
                    ></template
                  ></a-alert
                >
                <a-form-item label="业务对象范围"
                  ><a-select
                    v-model:value="form.entity_ids"
                    mode="multiple"
                    :options="entityOptions"
                    :disabled="!editable || !form.ontology_version_id"
                    :loading="catalogLoading"
                    placeholder="选择该技能需要访问的对象"
                /></a-form-item>
                <a-form-item label="引用业务函数"
                  ><a-select
                    :value="selectedFunctions"
                    mode="multiple"
                    :options="functionOptions"
                    :disabled="!editable || !form.ontology_version_id"
                    :loading="catalogLoading"
                    placeholder="选择计算、规则判断等能力"
                    @update:value="setTools('function', $event)"
                /></a-form-item>
                <a-form-item label="引用业务行动"
                  ><a-select
                    :value="selectedActions"
                    mode="multiple"
                    :options="actionOptions"
                    :disabled="!editable || !form.ontology_version_id"
                    :loading="catalogLoading"
                    placeholder="选择创建工单等业务操作"
                    @update:value="setTools('action', $event)"
                  />
                  <p class="field-help">
                    行动执行受智能体权限与确认规则约束。技能测试采用行动模拟，不产生业务写入。
                  </p></a-form-item
                >
              </a-form>
              <a-alert
                v-if="catalogError"
                :message="catalogError"
                type="error"
                show-icon
                class="section-alert"
                ><template #action
                  ><a-button size="small" @click="loadCatalog">重试</a-button></template
                ></a-alert
              >
              <div class="section-heading">
                <div>
                  <h2>输入与输出</h2>
                  <p>约定输入信息与结果结构，帮助复用方正确调用。</p>
                </div>
                <a-button size="small" @click="loadCatalog" :loading="catalogLoading"
                  >刷新依赖</a-button
                >
              </div>
              <SkillSchemaEditor
                v-model="form.input_schema"
                title="输入结构"
                :disabled="!editable"
                @validity="inputValid = $event"
              />
              <SkillSchemaEditor
                v-model="form.output_schema"
                title="输出结构"
                :disabled="!editable"
                @validity="outputValid = $event"
              />
            </a-tab-pane>
            <a-tab-pane key="assets" tab="参考资料">
              <div class="section-heading">
                <div>
                  <h2>参考资料</h2>
                  <p>选择资产目录中的规程、手册和业务数据，为执行提供依据。</p>
                </div>
                <a-button size="small" @click="loadCatalog" :loading="catalogLoading"
                  >刷新资料</a-button
                >
              </div>
              <a-select
                v-model:value="form.asset_refs"
                mode="multiple"
                :disabled="!editable"
                :options="assetOptions"
                :loading="catalogLoading"
                style="width: 100%"
                placeholder="搜索并选择参考资料"
                option-filter-prop="label"
              />
              <a-alert
                v-if="catalogError"
                :message="catalogError"
                type="error"
                show-icon
                class="section-alert"
              />
              <div v-if="form.asset_refs.length" class="assets-list">
                <div v-for="id in form.asset_refs" :key="id" class="asset-row">
                  <div>
                    <strong>{{ assetName(id) }}</strong>
                    <p>
                      {{
                        catalog.assets.find((a) => a.id === id)?.description ||
                        '作为业务技能的参考依据'
                      }}
                    </p>
                  </div>
                  <a-button type="link" @click="previewAsset(id)">查看资产</a-button
                  ><a-button
                    v-if="editable"
                    type="text"
                    danger
                    @click="form.asset_refs = form.asset_refs.filter((a) => a !== id)"
                    >移除</a-button
                  >
                </div>
              </div>
              <a-empty
                v-else
                description="尚未选择参考资料；无外部参考要求的技能可以不绑定"
                class="section-empty"
              />
            </a-tab-pane>
            <a-tab-pane key="tests" tab="测试与版本">
              <div class="section-heading">
                <div>
                  <h2>测试用例</h2>
                  <p>使用真实业务问题验证结果关键词和能力调用。发布要求当前草稿通过运行测试。</p>
                </div>
                <a-space
                  ><a-button
                    :disabled="!saved || testing || validating"
                    @click="validate"
                    :loading="validating"
                    >校验依赖</a-button
                  ><a-button v-if="editable" @click="addCase">＋ 添加用例</a-button
                  ><a-button
                    type="primary"
                    :disabled="!saved || !form.test_cases.length || !editable"
                    :loading="testing"
                    @click="runTests()"
                    >运行全部</a-button
                  ></a-space
                >
              </div>
              <a-alert
                v-if="dirty"
                type="warning"
                show-icon
                message="测试前会先保存当前草稿，以确保记录与发布内容一致。"
                class="section-alert"
              />
              <a-alert
                v-if="validation"
                :type="validation.valid ? 'success' : 'error'"
                :message="validation.valid ? '依赖与结构校验通过' : '校验未通过'"
                show-icon
                class="section-alert"
                ><template #description
                  ><div v-for="(message, i) in validationMessages" :key="i">
                    {{ message }}
                  </div></template
                ></a-alert
              >
              <div v-for="(test, i) in form.test_cases" :key="test.id" class="test-card">
                <div class="test-top">
                  <strong>{{ test.name || `测试用例 ${i + 1}` }}</strong
                  ><a-space v-if="editable"
                    ><a-button
                      type="link"
                      size="small"
                      :disabled="!saved || testing"
                      @click="runTests(test.id)"
                      >运行</a-button
                    ><a-button type="link" size="small" :disabled="testing" @click="editCase(i)"
                      >编辑</a-button
                    ><a-button
                      type="link"
                      size="small"
                      danger
                      :disabled="testing"
                      @click="form.test_cases.splice(i, 1)"
                      >移除</a-button
                    ></a-space
                  >
                </div>
                <p class="test-question">
                  {{ typeof test.input === 'string' ? test.input : JSON.stringify(test.input) }}
                </p>
                <div class="test-criteria">
                  <span>预期关键词：{{ test.expected_keywords.join('、') || '无' }}</span
                  ><span>预期调用：{{ test.expected_tools.map(toolName).join('、') || '无' }}</span>
                </div>
              </div>
              <a-empty
                v-if="!form.test_cases.length"
                description="添加至少一个测试用例，验证业务方法是否有效"
                class="section-empty"
              />
              <h2 class="sub-heading">最近测试记录</h2>
              <a-collapse v-if="testRuns.length" class="test-runs"
                ><a-collapse-panel v-for="run in testRuns" :key="run.id"
                  ><template #header
                    ><a-tag
                      :color="
                        run.status === 'passed'
                          ? 'green'
                          : run.status === 'not_run'
                            ? 'orange'
                            : 'red'
                      "
                      >{{
                        run.status === 'passed'
                          ? '通过'
                          : run.status === 'not_run'
                            ? '未运行'
                            : '未通过'
                      }}</a-tag
                    ><span
                      >{{ formatDate(run.created_at) }} ·
                      {{ run.validation_level === 'runtime' ? '业务运行测试' : '前置校验' }}</span
                    ></template
                  ><a-alert
                    v-if="run.errors?.length"
                    :message="run.errors.join('；')"
                    type="error"
                    show-icon
                    class="section-alert"
                  />
                  <div v-for="result in run.case_results" :key="result.id" class="run-case">
                    <strong>{{ result.name }}</strong
                    ><a-tag :color="result.passed ? 'green' : 'red'">{{
                      result.passed ? '通过' : '失败'
                    }}</a-tag>
                    <p v-if="result.answer" class="run-answer">{{ result.answer }}</p>
                    <div v-if="result.errors?.length" class="error-text">
                      {{ result.errors.join('；') }}
                    </div>
                    <details v-if="result.tool_runs?.length">
                      <summary>查看能力调用（{{ result.tool_runs.length }}）</summary>
                      <pre>{{ JSON.stringify(result.tool_runs, null, 2) }}</pre>
                    </details>
                  </div></a-collapse-panel
                ></a-collapse
              >
              <p v-else class="empty-inline">尚无测试记录</p>
              <div class="section-heading version-heading">
                <div>
                  <h2>发布版本</h2>
                  <p>已发布版本保留完整定义。新版本不会自动替换智能体的现有引用。</p>
                </div>
              </div>
              <a-table
                :columns="versionColumns"
                :data-source="versions"
                row-key="version"
                size="small"
                :pagination="false"
                ><template #bodyCell="{ column, record }"
                  ><template v-if="column.key === 'version'"
                    >v{{ record.version
                    }}<a-tag
                      v-if="record.version === saved?.current_version"
                      color="green"
                      style="margin-left: 8px"
                      >最新</a-tag
                    ></template
                  ><template v-else-if="column.key === 'time'">{{
                    formatDate(record.created_at)
                  }}</template
                  ><template v-else-if="column.key === 'action'"
                    ><a-button type="link" size="small" @click="showVersion(record.version)"
                      >查看定义</a-button
                    ></template
                  ></template
                ><template #emptyText>尚未发布版本</template></a-table
              >
            </a-tab-pane>
          </a-tabs>
        </section>
        <aside class="detail-aside">
          <section class="aside-card">
            <h3>技能概况</h3>
            <dl>
              <dt>关联本体</dt>
              <dd>{{ ontologyName }}</dd>
              <dt>发布版本</dt>
              <dd>{{ saved?.current_version ? `v${saved.current_version}` : '尚未发布' }}</dd>
              <dt>可用能力</dt>
              <dd>{{ form.tools.length }} 项 · {{ form.entity_ids.length }} 类对象</dd>
              <dt>最近保存</dt>
              <dd>{{ formatDate(saved?.updated_at) }}</dd>
            </dl>
          </section>
          <section class="aside-card">
            <h3>
              智能体引用 <span>{{ referencedAgentCount }}</span>
            </h3>
            <p class="aside-help">固定版本保证在线行为稳定。版本更新后，由智能体负责人选择升级。</p>
            <div
              v-for="reference in references"
              :key="`${reference.agent_id}-${reference.agent_version || ''}-${reference.version}-${reference.source}`"
              class="reference-item"
            >
              <RouterLink :to="`/agent/manage/${reference.agent_id}`">{{
                reference.agent_name || reference.name || '智能体'
              }}</RouterLink
              ><span
                >v{{ reference.version || reference.skill_version }} ·
                {{
                  reference.source === 'published'
                    ? `发布定义 v${reference.agent_version || ''}`
                    : '配置草稿'
                }}</span
              ><a-tag
                v-if="
                  (reference.version || reference.skill_version || 0) <
                  (saved?.current_version || 0)
                "
                color="orange"
                >可升级</a-tag
              >
            </div>
            <p v-if="!references.length" class="empty-inline">尚未被智能体引用</p>
          </section>
          <section class="aside-card guide-card">
            <h3>编写建议</h3>
            <p>明确适用边界、判断顺序和输出依据。将计算交给业务函数，将操作交给业务行动。</p>
            <p>为典型任务、异常信息和边界条件添加测试，发布前检查全部结果。</p>
          </section>
        </aside>
      </div>
      <a-modal
        v-model:open="caseOpen"
        :title="caseIndex < 0 ? '添加测试用例' : '编辑测试用例'"
        ok-text="保存用例"
        cancel-text="取消"
        @ok="saveCase"
        width="640px"
        ><a-form layout="vertical"
          ><a-form-item label="用例名称" required
            ><a-input
              v-model:value="caseDraft.name"
              placeholder="例如：温度异常的诊断建议" /></a-form-item
          ><a-form-item label="业务问题" required
            ><a-textarea
              v-model:value="caseInput"
              :rows="4"
              placeholder="输入智能体需要完成的业务任务" /></a-form-item
          ><a-form-item label="结果应包含的关键词"
            ><a-select
              v-model:value="caseDraft.expected_keywords"
              mode="tags"
              placeholder="输入关键词并按回车" /></a-form-item
          ><a-form-item label="预期调用的能力"
            ><a-select
              v-model:value="caseDraft.expected_tools"
              mode="multiple"
              :options="expectedToolOptions"
              placeholder="选择本体查询或已绑定的业务能力" /></a-form-item
        ></a-form>
        <p class="field-help">
          关键词用于核验结果；预期能力用于核验执行是否覆盖必要步骤。业务行动会模拟执行。
        </p></a-modal
      >
      <a-modal
        v-model:open="publishOpen"
        title="发布业务技能新版本"
        ok-text="确认发布"
        cancel-text="取消"
        :confirm-loading="publishing"
        @ok="publish"
        ><a-alert
          type="info"
          show-icon
          :message="`将发布 v${(saved?.current_version || 0) + 1}。已有 ${references.length} 项引用继续使用原版本。`"
        /><a-form layout="vertical" style="margin-top: 20px"
          ><a-form-item label="版本说明" required
            ><a-textarea
              v-model:value="publishDescription"
              :rows="3"
              placeholder="说明本次业务方法、依赖或输出有哪些变化" /></a-form-item
        ></a-form>
        <p class="field-help">
          当前内容必须通过业务运行测试；发布时会再次验证，已发布定义保持不变。
        </p></a-modal
      >
      <a-drawer
        v-model:open="versionOpen"
        :title="`已发布定义 · v${selectedVersion?.version || ''}`"
        width="760px"
        ><a-spin :spinning="versionLoading"
          ><template v-if="versionSnapshot"
            ><a-alert
              type="info"
              message="这是发布时保存的定义，可用于审阅和对照当前草稿。"
              show-icon
            />
            <h3>{{ versionSnapshot.name }}</h3>
            <p>{{ versionSnapshot.description }}</p>
            <h4>操作指引</h4>
            <pre class="snapshot-content">{{ versionSnapshot.prompt_template }}</pre>
            <h4>完整定义</h4>
            <pre class="snapshot-content">{{ JSON.stringify(versionSnapshot, null, 2) }}</pre>
          </template></a-spin
        ></a-drawer
      >
      <AssetDetailDrawer v-model:visible="assetPreviewOpen" :asset-id="assetPreviewId" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import {
  skillsApi,
  skillError,
  type SkillCatalog,
  type SkillItem,
  type SkillReference,
  type SkillTestCase,
  type SkillTestRun,
  type SkillValidation,
  type SkillVersion,
} from '../../api/skills'
import SkillSchemaEditor from '../../components/skills/SkillSchemaEditor.vue'
import AssetDetailDrawer from '../../components/asset/AssetDetailDrawer.vue'
import { useToast } from '../../composables/useToast'
import { useAuthStore } from '../../store/auth'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const authStore = useAuthStore()
const roleCanEdit = computed(() => ['admin', 'editor'].includes(authStore.user?.role || ''))
const emptySkill = (): SkillItem => ({
  id: '',
  name: '',
  description: '',
  prompt_template: '',
  input_schema: { type: 'object', properties: {} },
  output_schema: { type: 'object', properties: {} },
  tools: [],
  test_cases: [],
  asset_refs: [],
  ontology_id: null,
  ontology_version_id: null,
  entity_ids: [],
  applicable_tasks: '',
  excluded_tasks: '',
  owner_team: '',
  visibility: 'workspace',
  tags: [],
  status: 'draft',
  current_version: 0,
  has_changes: false,
  ref_count: 0,
  can_edit: true,
})
const form = ref<SkillItem>(emptySkill())
const saved = ref<SkillItem | null>(null)
const baseline = ref('')
const loading = ref(true)
const loadError = ref('')
const formError = ref('')
const saving = ref(false)
const testing = ref(false)
const validating = ref(false)
const publishing = ref(false)
const archiving = ref(false)
const tab = ref('instructions')
const inputValid = ref(true)
const outputValid = ref(true)
const catalog = ref<SkillCatalog>({
  ontologies: [],
  ontology_versions: [],
  entities: [],
  functions: [],
  actions: [],
  assets: [],
})
const catalogLoading = ref(false)
const catalogError = ref('')
const versions = ref<SkillVersion[]>([])
const references = ref<SkillReference[]>([])
const testRuns = ref<SkillTestRun[]>([])
const validation = ref<SkillValidation | null>(null)
const canManage = computed(() => roleCanEdit.value && saved.value?.can_edit !== false)
const canEditContent = computed(() => canManage.value && form.value.status !== 'archived')
const editable = computed(
  () =>
    canEditContent.value &&
    !saving.value &&
    !testing.value &&
    !publishing.value &&
    !validating.value,
)
const dirty = computed(
  () =>
    !loading.value &&
    !loadError.value &&
    (JSON.stringify(form.value) !== baseline.value || !inputValid.value || !outputValid.value),
)
const statusLabel = computed(
  () => ({ draft: '草稿', active: '已发布', archived: '已归档' })[form.value.status],
)
const ontologyName = computed(
  () =>
    catalog.value.ontologies?.find((o) => o.id === form.value.ontology_id)?.name ||
    (form.value.ontology_id ? '关联本体' : '通用技能'),
)
const ontologyOptions = computed(() =>
  (catalog.value.ontologies || []).map((o) => ({ value: o.id, label: o.name })),
)
const versionOptions = computed(() =>
  catalog.value.ontology_versions
    .filter((v) => !form.value.ontology_id || v.ontology_id === form.value.ontology_id)
    .map((v) => ({
      value: v.id,
      label: `v${v.version_number ?? v.version ?? ''} · ${v.name || '本体版本'}`,
    })),
)
const label = (item: { name: string; name_cn?: string; display_name?: string }) =>
  item.name_cn || item.display_name || item.name
const entityOptions = computed(() =>
  catalog.value.entities.map((v) => ({ value: v.id, label: label(v) })),
)
const functionOptions = computed(() =>
  catalog.value.functions.map((v) => ({ value: v.id, label: label(v) })),
)
const actionOptions = computed(() =>
  catalog.value.actions.map((v) => ({ value: v.id, label: label(v) })),
)
const assetOptions = computed(() =>
  catalog.value.assets.map((v) => ({ value: v.id, label: label(v) })),
)
const selectedFunctions = computed(() =>
  form.value.tools.filter((t) => t.type === 'function').map((t) => t.id),
)
const selectedActions = computed(() =>
  form.value.tools.filter((t) => t.type === 'action').map((t) => t.id),
)
const expectedToolOptions = computed(() => [
  { value: 'query_entity_data', label: '查询业务对象数据' },
  { value: 'get_entity_detail', label: '读取对象定义' },
  { value: 'describe_ontology_model', label: '理解本体结构' },
  ...form.value.tools.map((t) => ({ value: t.id, label: toolName(t.id) })),
])
const validationMessages = computed(() =>
  [...(validation.value?.errors || []), ...(validation.value?.warnings || [])].map((m) =>
    typeof m === 'string' ? m : m.message,
  ),
)
const referencedAgentCount = computed(() => new Set(references.value.map((r) => r.agent_id)).size)
const versionColumns = [
  { title: '版本', key: 'version' },
  { title: '版本说明', dataIndex: 'description' },
  { title: '发布时间', key: 'time' },
  { title: '操作', key: 'action' },
]
let catalogRequest = 0
function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value))
}
function normalize(item: SkillItem): SkillItem {
  return { ...emptySkill(), ...item }
}
function adopt(item: SkillItem) {
  const normalized = normalize(item)
  saved.value = clone(normalized)
  form.value = clone(normalized)
  baseline.value = JSON.stringify(form.value)
  inputValid.value = true
  outputValid.value = true
}
let loadRequest = 0
let historyRequest = 0
let versionRequest = 0
async function load() {
  const request = ++loadRequest
  const id = String(route.params.id || '')
  catalogRequest++
  historyRequest++
  versionRequest++
  versionOpen.value = false
  publishOpen.value = false
  caseOpen.value = false
  assetPreviewOpen.value = false
  loading.value = true
  loadError.value = ''
  formError.value = ''
  validation.value = null
  versions.value = []
  references.value = []
  testRuns.value = []
  try {
    if (!authStore.user) await authStore.fetchUser()
    if (id) {
      const item = await skillsApi.get(id)
      if (request !== loadRequest) return
      adopt(item)
    } else {
      saved.value = null
      form.value = emptySkill()
      baseline.value = JSON.stringify(form.value)
    }
    if (request !== loadRequest) return
    await loadCatalog()
    if (request !== loadRequest) return
    if (saved.value) await loadHistory()
  } catch (e) {
    if (request === loadRequest) loadError.value = skillError(e, '技能加载失败')
  } finally {
    if (request === loadRequest) loading.value = false
  }
}
async function loadCatalog() {
  const request = ++catalogRequest
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const value = await skillsApi.catalog(
      form.value.ontology_id || undefined,
      form.value.ontology_version_id || undefined,
    )
    if (request === catalogRequest) catalog.value = value
  } catch (e) {
    if (request === catalogRequest) catalogError.value = skillError(e, '依赖加载失败')
  } finally {
    if (request === catalogRequest) catalogLoading.value = false
  }
}
async function loadHistory() {
  if (!saved.value) return
  const request = ++historyRequest
  const id = saved.value.id
  const result = await Promise.allSettled([
    skillsApi.versions(id),
    skillsApi.references(id),
    skillsApi.testRuns(id),
  ])
  if (request !== historyRequest || saved.value?.id !== id) return
  if (result[0].status === 'fulfilled') versions.value = result[0].value
  if (result[1].status === 'fulfilled') references.value = result[1].value
  if (result[2].status === 'fulfilled') testRuns.value = result[2].value
  const failed = result.filter((r) => r.status === 'rejected')
  if (failed.length) toast.error('部分版本、引用或测试记录加载失败，请刷新页面重试')
}
function changeOntology(value: string | undefined) {
  if ((value || null) === form.value.ontology_id) return
  confirmScopeChange(() => {
    form.value.ontology_id = value || null
    form.value.ontology_version_id = null
  })
}
function changeOntologyVersion(value: string | undefined) {
  if ((value || null) === form.value.ontology_version_id) return
  confirmScopeChange(() => {
    form.value.ontology_version_id = value || null
  })
}
function confirmScopeChange(change: () => void) {
  const apply = () => {
    change()
    form.value.entity_ids = []
    form.value.tools = []
    form.value.asset_refs = []
    validation.value = null
    catalog.value.entities = []
    catalog.value.functions = []
    catalog.value.actions = []
    catalog.value.assets = []
    loadCatalog()
  }
  if (form.value.entity_ids.length || form.value.tools.length || form.value.asset_refs.length) {
    Modal.confirm({
      title: '变更技能的本体范围？',
      content:
        '原有对象、业务能力和资料引用将清空。技能说明和测试用例会保留，请重新选择依赖并检查测试预期。',
      okText: '变更范围',
      cancelText: '保留当前范围',
      onOk: apply,
    })
  } else apply()
}
function setTools(type: 'function' | 'action', ids: string[]) {
  form.value.tools = [
    ...form.value.tools.filter((t) => t.type !== type),
    ...ids.map((id) => ({ type, id })),
  ]
}
function assetName(id: string) {
  return catalog.value.assets.find((a) => a.id === id)?.name || '资料已不可用'
}
function toolName(id: string) {
  const item = [...catalog.value.functions, ...catalog.value.actions].find((t) => t.id === id)
  return (
    item?.name ||
    (
      {
        query_entity_data: '查询业务对象数据',
        get_entity_detail: '读取对象定义',
        describe_ontology_model: '理解本体结构',
      } as Record<string, string>
    )[id] ||
    id
  )
}
function formatDate(value?: string) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('zh-CN', { hour12: false })
}
async function save(): Promise<boolean> {
  if (saving.value || testing.value || publishing.value || validating.value || archiving.value)
    return false
  if (!canManage.value || form.value.status === 'archived') return false
  if (!inputValid.value || !outputValid.value) {
    formError.value = '输入或输出结构格式不正确，请在“本体与工具”中修正'
    tab.value = 'dependencies'
    return false
  }
  if (!form.value.name.trim()) {
    formError.value = '请填写技能名称'
    tab.value = 'instructions'
    return false
  }
  saving.value = true
  formError.value = ''
  try {
    const {
      name,
      description,
      prompt_template,
      input_schema,
      output_schema,
      tools,
      test_cases,
      asset_refs,
      ontology_id,
      ontology_version_id,
      entity_ids,
      applicable_tasks,
      excluded_tasks,
      owner_team,
      visibility,
      tags,
    } = form.value
    const payload = clone({
      name,
      description,
      prompt_template,
      input_schema,
      output_schema,
      tools,
      test_cases,
      asset_refs,
      ontology_id,
      ontology_version_id,
      entity_ids,
      applicable_tasks,
      excluded_tasks,
      owner_team,
      visibility,
      tags,
    })
    const item = saved.value
      ? await skillsApi.update(saved.value.id, payload)
      : await skillsApi.create(payload)
    adopt(item)
    validation.value = null
    toast.success('技能草稿已保存')
    if (!route.params.id) {
      saving.value = false
      await router.replace(`/skills/${item.id}`)
    }
    return true
  } catch (e) {
    formError.value = skillError(e, '保存失败')
    return false
  } finally {
    saving.value = false
  }
}
async function ensureSaved() {
  return saved.value && !dirty.value ? true : await save()
}
async function validate() {
  if (!(await ensureSaved()) || !saved.value) return
  validating.value = true
  try {
    validation.value = await skillsApi.validate(saved.value.id)
  } catch (e) {
    formError.value = skillError(e, '校验失败')
  } finally {
    validating.value = false
  }
}
async function runTests(caseId?: string) {
  if (!(await ensureSaved()) || !saved.value) return
  testing.value = true
  formError.value = ''
  try {
    const run = await skillsApi.test(
      saved.value.id,
      caseId ? { test_case_ids: [caseId] } : undefined,
    )
    testRuns.value = [run, ...testRuns.value.filter((r) => r.id !== run.id)]
    if (run.status === 'passed') toast.success('业务运行测试通过')
    else if (run.status === 'not_run') toast.warning('测试尚未运行，请查看记录中的原因')
    else toast.error('测试未通过，请查看用例结果')
  } catch (e) {
    formError.value = skillError(e, '测试失败')
  } finally {
    testing.value = false
  }
}
async function preparePublish() {
  if (!(await ensureSaved()) || !saved.value) return
  tab.value = 'tests'
  validating.value = true
  try {
    validation.value = await skillsApi.validate(saved.value.id)
    if (!validation.value.valid) {
      formError.value = '请先修正校验问题，再运行测试并发布'
      return
    }
    const tested = new Set(
      testRuns.value
        .filter(
          (run) =>
            run.validation_level === 'runtime' &&
            run.passed &&
            run.fingerprint === validation.value?.fingerprint,
        )
        .flatMap((run) =>
          (run.case_results || []).filter((result) => result.passed).map((result) => result.id),
        ),
    )
    const pending = form.value.test_cases.filter((test) => !tested.has(test.id))
    if (pending.length) {
      formError.value = `发布前还需验证 ${pending.length} 个当前内容的用例，请先运行测试：${pending.map((test) => test.name).join('、')}`
      return
    }
    publishDescription.value = ''
    publishOpen.value = true
  } catch (e) {
    formError.value = skillError(e)
  } finally {
    validating.value = false
  }
}
const publishOpen = ref(false)
const publishDescription = ref('')
async function publish() {
  if (!publishDescription.value.trim()) {
    toast.warning('请填写版本说明')
    return
  }
  if (!saved.value) return
  publishing.value = true
  try {
    adopt(await skillsApi.publish(saved.value.id, publishDescription.value.trim()))
    publishOpen.value = false
    await loadHistory()
    toast.success(`已发布技能 v${saved.value.current_version}`)
  } catch (e) {
    formError.value = skillError(e, '发布失败')
    toast.error(formError.value)
  } finally {
    publishing.value = false
  }
}
function toggleArchive() {
  if (!saved.value) return
  const restore = saved.value.status === 'archived'
  Modal.confirm({
    title: restore ? '恢复此技能？' : '归档此技能？',
    content: restore
      ? '恢复后可以继续编辑、测试和发布。'
      : '归档后不再允许新挂载；已有版本与智能体引用保留。未保存修改不会被保存。',
    okText: restore ? '恢复' : '归档',
    cancelText: '取消',
    async onOk() {
      if (!saved.value) return
      archiving.value = true
      try {
        adopt(
          await (restore ? skillsApi.restore(saved.value.id) : skillsApi.archive(saved.value.id)),
        )
        toast.success(restore ? '技能已恢复' : '技能已归档')
      } catch (e) {
        toast.error(skillError(e))
        throw e
      } finally {
        archiving.value = false
      }
    },
  })
}
const caseOpen = ref(false)
const caseIndex = ref(-1)
const caseInput = ref('')
const caseDraft = ref<SkillTestCase>({
  id: '',
  name: '',
  input: '',
  expected_keywords: [],
  expected_tools: [],
})
function addCase() {
  caseIndex.value = -1
  caseDraft.value = {
    id: crypto.randomUUID(),
    name: '',
    input: '',
    expected_keywords: [],
    expected_tools: [],
  }
  caseInput.value = ''
  caseOpen.value = true
}
function editCase(index: number) {
  caseIndex.value = index
  caseDraft.value = clone(form.value.test_cases[index]!)
  caseInput.value =
    typeof caseDraft.value.input === 'string'
      ? caseDraft.value.input
      : JSON.stringify(caseDraft.value.input, null, 2)
  caseOpen.value = true
}
function saveCase() {
  if (!caseDraft.value.name.trim() || !caseInput.value.trim()) {
    toast.warning('请填写用例名称和业务问题')
    return
  }
  if (!caseDraft.value.expected_keywords.length && !caseDraft.value.expected_tools.length) {
    toast.warning('请设置至少一个预期关键词或预期调用能力')
    return
  }
  caseDraft.value.input = caseInput.value.trim()
  if (caseIndex.value < 0) form.value.test_cases.push(clone(caseDraft.value))
  else form.value.test_cases[caseIndex.value] = clone(caseDraft.value)
  caseOpen.value = false
}
const versionOpen = ref(false)
const versionLoading = ref(false)
const selectedVersion = ref<SkillVersion | null>(null)
const versionSnapshot = computed(
  () =>
    selectedVersion.value?.snapshot_json ||
    selectedVersion.value?.snapshot ||
    selectedVersion.value?.definition,
)
const assetPreviewOpen = ref(false)
const assetPreviewId = ref<string | null>(null)
function previewAsset(id: string) {
  assetPreviewId.value = id
  assetPreviewOpen.value = true
}
async function showVersion(version: number) {
  if (!saved.value) return
  const request = ++versionRequest
  const id = saved.value.id
  versionOpen.value = true
  versionLoading.value = true
  selectedVersion.value = null
  try {
    const result = await skillsApi.version(id, version)
    if (request === versionRequest && saved.value?.id === id) selectedVersion.value = result
  } catch (e) {
    if (request === versionRequest) toast.error(skillError(e, '版本定义加载失败'))
  } finally {
    if (request === versionRequest) versionLoading.value = false
  }
}
function confirmLeave() {
  if (saving.value || testing.value || publishing.value || validating.value || archiving.value) {
    toast.info('操作正在进行，请等待完成后再离开')
    return false
  }
  if (!dirty.value) return true
  return new Promise<boolean>((resolve) =>
    Modal.confirm({
      title: '离开未保存的技能？',
      content: '当前修改尚未保存，离开后会丢失。',
      okText: '离开',
      cancelText: '继续编辑',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    }),
  )
}
onBeforeRouteLeave(confirmLeave)
onBeforeRouteUpdate(confirmLeave)
function beforeUnload(event: BeforeUnloadEvent) {
  if (dirty.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}
onMounted(() => {
  window.addEventListener('beforeunload', beforeUnload)
  load()
})
onBeforeUnmount(() => {
  loadRequest++
  catalogRequest++
  historyRequest++
  versionRequest++
  window.removeEventListener('beforeunload', beforeUnload)
})
watch(
  () => route.params.id,
  () => {
    if (!saving.value) load()
  },
)
</script>

<style scoped>
.skill-detail {
  max-width: 1560px;
  margin: auto;
}
.skill-detail--readonly :deep(.ant-input[disabled]),
.skill-detail--readonly :deep(.ant-select-disabled .ant-select-selector) {
  color: var(--neutral-700);
  cursor: default;
}
.detail-loading {
  display: block;
  padding: 100px;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 18px;
}
.back-link {
  background: none;
  border: none;
  color: #64748b;
  font-size: 12px;
  padding: 0;
  margin-bottom: 10px;
  cursor: pointer;
}
.detail-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.detail-title h1 {
  font-size: 23px;
  color: #1e293b;
  margin: 0;
  font-weight: 650;
}
.detail-title .ant-tag {
  margin: 0;
}
.detail-header p {
  font-size: 12px;
  color: #64748b;
  margin: 8px 0 0;
}
.detail-banner {
  margin-bottom: 14px;
}
.detail-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 268px;
  gap: 20px;
  align-items: start;
}
.detail-main {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0 24px 20px;
  min-width: 0;
}
.detail-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 24px;
}
.detail-tabs :deep(.ant-tabs-tab) {
  padding: 18px 0;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.field-help {
  font-size: 12px;
  color: #64748b;
  line-height: 1.7;
  margin: 8px 0 0;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin: 0 0 20px;
}
.section-heading h2 {
  font-size: 16px;
  color: #334155;
  margin: 0 0 6px;
}
.section-heading p {
  font-size: 12px;
  color: #64748b;
  margin: 0;
  line-height: 1.7;
}
.section-alert {
  margin: 14px 0;
}
.section-empty {
  padding: 36px 0;
}
.detail-aside {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.aside-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 18px;
}
.aside-card h3 {
  font-size: 14px;
  margin: 0 0 16px;
  color: #334155;
}
.aside-card h3 span {
  float: right;
  font-size: 12px;
  background: #eff6ff;
  border-radius: 4px;
  padding: 2px 7px;
  color: #2563eb;
}
.aside-card dl {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: 12px;
  font-size: 12px;
  margin: 0;
}
.aside-card dt {
  color: #64748b;
}
.aside-card dd {
  margin: 0;
  color: #334155;
  word-break: break-word;
}
.aside-help,
.guide-card p {
  font-size: 12px;
  color: #64748b;
  line-height: 1.8;
  margin: 0 0 12px;
}
.guide-card {
  background: #f8fafc;
}
.guide-card p:last-child {
  margin: 0;
}
.reference-item {
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
  font-size: 12px;
}
.reference-item a {
  font-weight: 500;
}
.reference-item span {
  color: #64748b;
}
.empty-inline {
  font-size: 12px;
  color: #94a3b8;
  margin: 12px 0;
}
.assets-list {
  margin-top: 20px;
}
.asset-row {
  padding: 18px 0;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  gap: 12px;
}
.asset-row > div {
  flex: 1;
}
.asset-row strong {
  font-size: 13px;
  color: #334155;
}
.asset-row p {
  font-size: 12px;
  color: #64748b;
  margin: 6px 0 0;
}
.test-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}
.test-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.test-top strong {
  font-size: 13px;
  color: #334155;
}
.test-question {
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
  white-space: pre-wrap;
  margin: 10px 0;
}
.test-criteria {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
  color: #64748b;
}
.sub-heading {
  font-size: 15px;
  color: #334155;
  margin: 28px 0 16px;
}
.test-runs {
  font-size: 12px;
}
.run-case {
  padding: 12px 0;
  border-top: 1px solid #e2e8f0;
}
.run-case strong {
  margin-right: 10px;
}
.run-answer {
  white-space: pre-wrap;
  line-height: 1.8;
}
.error-text {
  color: #b91c1c;
  font-size: 12px;
}
.run-case details {
  font-size: 12px;
  margin-top: 10px;
}
.run-case pre,
.snapshot-content {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 14px;
  line-height: 1.8;
  font-size: 12px;
}
.version-heading {
  margin-top: 30px;
}
@media (max-width: 1180px) {
  .detail-workspace {
    grid-template-columns: minmax(0, 1fr);
  }
  .detail-aside {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .guide-card {
    display: none;
  }
  .detail-header {
    align-items: flex-start;
  }
  .section-heading {
    flex-wrap: wrap;
  }
}
@media (max-width: 800px) {
  .detail-header {
    flex-wrap: wrap;
  }
  .form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
  .detail-main {
    padding: 0 14px 14px;
  }
  .detail-aside {
    grid-template-columns: 1fr;
  }
}
</style>
