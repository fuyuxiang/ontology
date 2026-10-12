<template>
  <div class="aw" @keydown.esc="drawer = null">
    <div v-if="loading" class="aw-empty">{{ text("正在加载智能体配置…") }}</div>
    <template v-else>
      <header class="aw-header">
        <div class="aw-row">
          <button class="aw-icon" :aria-label="text('返回智能体列表')" @click="router.push('/agent/manage')">
            ←
          </button>
          <h1>{{ form.name || text('未命名智能体') }}</h1>
          <span class="aw-pill aw-amber">{{ text("编辑草稿") }}</span
          ><span v-if="current?.current_version" class="aw-pill aw-green"
            >{{ current.status === 'published' ? text('在线') : text('最近发布') }} v{{
              current.current_version
            }}</span
          ><small class="aw-muted">{{ isDirty ? text('未保存 · 待验证') : text('已保存') }}</small>
        </div>
        <div class="aw-row">
          <button class="aw-button" :disabled="saving || chatBusy || !canEdit" @click="saveAgent">
            {{ saving ? text('保存中…') : text('保存草稿') }}</button
          ><button
            class="aw-button aw-primary"
            :disabled="!current || chatBusy || !canEdit"
            @click="drawer = 'publish'"
          >
            {{ text("发布") }}
          </button>
        </div>
      </header>
      <div v-if="error" class="aw-alert aw-error" role="alert">
        {{ error }}<button class="aw-link" @click="error = ''">{{ text("关闭") }}</button>
      </div>
      <div v-if="notice" class="aw-alert aw-success" role="status">{{ notice }}</div>
      <div v-if="!canEdit" class="aw-alert">
        {{ text("当前账号可查看；修改配置和发布需要写入权限，调试和行动授权分别需要对应的执行权限。") }}
      </div>
      <div v-if="current?.ontology_stale" class="aw-alert">
        {{ text("依赖本体已经变化，请核对版本与技能依赖并重新测试。") }}<button
          class="aw-link"
          @click="configTab = '本体与能力'"
        >
          {{ text("检查依赖") }}
        </button>
      </div>
      <nav class="aw-tabs" :aria-label="text('智能体工作台')">
        <button
          v-for="tab in workspaceTabs"
          :key="tab"
          :aria-selected="workspaceTab === tab"
          :class="{ active: workspaceTab === tab }"
          :disabled="chatBusy && workspaceTab !== tab"
          @click="selectWorkspaceTab(tab)"
        >
          {{ text(tab) }}
        </button>
      </nav>
      <div v-show="workspaceTab === '配置与调试'" class="aw-workbody">
        <section class="aw-config" :aria-label="text('智能体配置')">
          <nav class="aw-subtabs" :aria-label="text('配置分区')">
            <button
              v-for="tab in configTabs"
              :key="tab"
              :class="{ active: configTab === tab }"
              :aria-selected="configTab === tab"
              @click="configTab = tab"
            >
              {{ text(tab) }}
            </button>
          </nav>
          <fieldset :disabled="chatBusy || saving || !canEdit">
            <template v-if="configTab === '基本设置'">
              <label class="aw-field"
                ><span>{{ text("智能体名称") }} <b>*</b></span
                ><input v-model="form.name" maxlength="100" :placeholder="text('输入智能体名称')" /></label
              ><label class="aw-field"
                ><span>{{ text("业务目标") }}</span
                ><textarea
                  v-model="form.description"
                  rows="4"
                  :placeholder="text('希望智能体帮助完成什么业务任务？')"
                ></textarea></label
              ><label class="aw-field"
                ><span>{{ text("模型") }}</span
                ><select v-model="form.model_id">
                  <option value="">{{ text("平台默认模型") }}</option>
                  <option v-for="model in activeModels" :key="model.id" :value="model.id">
                    {{ model.name }} · {{ model.model_name }}
                  </option>
                  <option
                    v-if="form.model_id && !activeModels.some((m) => m.id === form.model_id)"
                    :value="form.model_id"
                    disabled
                  >
                    {{ text("原模型已停用或不可访问") }}
                  </option></select
                ><small>{{ text("使用平台已配置且可用的模型。") }}</small></label
              ><label class="aw-field"
                ><span>{{ text("标签") }}</span
                ><input v-model="form.tagsStr" :placeholder="text('用逗号分隔，例如：设备运维,分析')"
              /></label>
            </template>
            <template v-else-if="configTab === '本体与能力'">
              <h2>{{ text("业务上下文") }}</h2>
              <label class="aw-field"
                ><span>{{ text("关联已发布本体") }} <b>*</b></span
                ><select v-model="form.ontology_id" @change="changeOntology">
                  <option value="">{{ text("请选择本体") }}</option>
                  <option
                    v-for="ontology in ontologies"
                    :key="ontology.ontology_id"
                    :value="ontology.ontology_id"
                  >
                    {{ ontology.name }}
                  </option>
                </select></label
              ><label class="aw-field"
                ><span>{{ text("固定本体版本") }} <b>*</b></span
                ><select
                  v-model="form.ontology_version_id"
                  :disabled="!form.ontology_id"
                  @change="changeOntologyVersion"
                >
                  <option value="">{{ text("请选择已发布版本") }}</option>
                  <option v-for="version in ontologyVersions" :key="version.id" :value="version.id">
                    v{{ version.version_number }} · {{ version.name
                    }}{{ version.is_active ? text('（当前）') : '' }}
                  </option>
                  <option
                    v-if="
                      form.ontology_version_id &&
                      !ontologyVersions.some((v) => v.id === form.ontology_version_id)
                    "
                    :value="form.ontology_version_id"
                    disabled
                  >
                    {{ text("原本体版本不可用") }}
                  </option>
                </select></label
              >
              <div v-if="catalogLoading" class="aw-muted">{{ text("正在读取版本对象与能力…") }}</div>
              <div v-else-if="form.ontology_version_id" class="aw-card">
                <div class="aw-row aw-between">
                  <h3>{{ text("可访问的对象范围") }}</h3>
                  <button
                    class="aw-link"
                    @click="form.entity_ids = catalog.entities.map(entitySourceId)"
                  >
                    {{ text("选择全部") }}
                  </button>
                </div>
                <label v-for="entity in catalog.entities" :key="entity.id" class="aw-checkbox"
                  ><input
                    v-model="form.entity_ids"
                    type="checkbox"
                    :value="entitySourceId(entity)"
                  /><span>{{ entity.name_cn || entity.display_name || entity.name }}</span></label
                >
                <p v-if="!catalog.entities.length" class="aw-muted">{{ text("该发布版本没有可用对象。") }}</p>
                <small class="aw-muted">{{ text("技能依赖对象必须在所选范围内。") }}</small>
              </div>
              <div class="aw-row aw-between aw-section-title">
                <h2>{{ text("挂载的业务技能") }}</h2>
                <button
                  class="aw-link"
                  :disabled="!form.ontology_version_id || catalogLoading"
                  @click="openSkillDrawer"
                >
                  {{ text("+ 添加技能") }}
                </button>
              </div>
              <p v-if="!form.skill_bindings.length" class="aw-empty aw-empty-compact">
                {{ text("尚未挂载技能，从已发布技能中选择业务能力。") }}
              </p>
              <article
                v-for="binding in form.skill_bindings"
                :key="binding.skill_id"
                class="aw-card aw-skill-card"
              >
                <div class="aw-row aw-between">
                  <h3>{{ boundSkill(binding)?.name || skillName(binding.skill_id) }}</h3>
                  <span class="aw-pill aw-blue">v{{ binding.version }}</span>
                </div>
                <p class="aw-muted">
                  {{ boundSkill(binding)?.description || text('正在读取固定版本…') }}
                </p>
                <div class="aw-row">
                  <span class="aw-pill"
                    >{{ boundSkill(binding)?.entity_ids?.length || 0 }} 项对象依赖</span
                  ><span class="aw-pill"
                    >{{ boundSkill(binding)?.tools?.length || 0 }} 项逻辑 / 动作</span
                  >
                </div>
                <p v-for="problem in bindingProblems(binding)" :key="problem" class="aw-text-error">
                  {{ problem }}
                </p>
                <footer class="aw-row aw-between">
                  <small>{{ text("固定使用已发布版本") }}</small>
                  <div class="aw-row">
                    <button class="aw-link" @click="router.push(`/skills/${binding.skill_id}`)">
                      查看</button
                    ><button
                      v-if="latestSkillVersion(binding.skill_id) > binding.version"
                      class="aw-link"
                      @click="reviewUpgrade(binding)"
                    >
                      升级到 v{{ latestSkillVersion(binding.skill_id) }}</button
                    ><button class="aw-link aw-danger" @click="unmountSkill(binding)">{{ text("卸载") }}</button>
                  </div>
                </footer>
              </article>
              <div
                v-if="availableFunctions.length || availableActions.length"
                class="aw-section-title"
              >
                <h2>{{ text("本体基础能力") }}</h2>
                <p class="aw-muted aw-small">{{ text("逻辑和动作在本体中维护，挂载技能不会扩大访问权限。") }}</p>
                <div class="aw-row">
                  <span v-for="item in availableFunctions" :key="item.id" class="aw-pill aw-blue"
                    >逻辑 · {{ item.name }}</span
                  ><span v-for="item in availableActions" :key="item.id" class="aw-pill aw-amber"
                    >动作 · {{ item.name }}</span
                  >
                </div>
              </div>
            </template>
            <template v-else
              ><label class="aw-field"
                ><span>{{ text("行为指引") }}</span
                ><textarea
                  v-model="form.system_prompt"
                  rows="13"
                  :placeholder="text('定义智能体目标、如何使用证据、信息不足时的处理与输出要求。')"
                ></textarea>
              </label>
              <h2>{{ text("运行方式") }}</h2>
              <label class="aw-field"><span>{{ text("执行路径") }}</span><select v-model="form.execution_mode"><option value="react">{{ text("ReAct 对话与工具") }}</option><option value="graph">{{ text("图执行") }}</option></select></label>
              <template v-if="form.execution_mode === 'graph'">
                <label class="aw-field"><span>{{ text("图定义（nodes / edges JSON）") }}</span><textarea v-model="form.graph_json" rows="14" spellcheck="false"></textarea></label>
                <p v-if="graphProblem" class="aw-text-error">{{ graphProblem }}</p>
                <label class="aw-field"><span>已发布业务动作</span><select v-model="graphActionId"><option value="">选择动作</option><option v-for="action in availableActions" :key="action.id" :value="action.id">{{ action.name }}</option></select></label>
                <button type="button" :disabled="!graphActionId" @click="setApprovalGraph">{{ text("生成输入 → 授权确认 → 输出图") }}</button>
                <p class="aw-muted">{{ text("在节点 data.params 中填写动作参数。函数和动作必须来自已绑定版本；确认模式会产生可授权的待执行记录。") }}</p>
              </template>
              <h2>{{ text("业务动作策略") }}</h2>
              <label class="aw-checkbox"
                ><input v-model="form.action_mode" type="radio" value="simulation" /><span
                  ><strong>{{ text("模拟执行") }}</strong
                  ><small>{{ text("首次默认使用模拟模式，业务写操作只返回预览。") }}</small></span
                ></label
              ><label class="aw-checkbox"
                ><input v-model="form.action_mode" type="radio" value="confirm" /><span
                  ><strong>{{ text("执行前授权确认") }}</strong
                  ><small
                    >{{ text("展示待执行动作和参数，由当前用户授权或拒绝；后端检查执行权限。") }}</small
                  ></span
                ></label
              ><label class="aw-field"
                ><span>{{ text("最多工具调用轮次") }}</span
                ><input
                  v-model.number="form.max_tool_rounds"
                  type="number"
                  min="2"
                  max="20" /></label
            ></template>
          </fieldset>
        </section>
        <AgentChatPanel
          :key="current?.id || 'new'"
          :agent-id="current?.id || null"
          :agent-name="form.name"
          :dirty="isDirty"
          :action-mode="form.action_mode"
          :can-authorize="canAuthorize"
          :can-confirm-actions="canConfirmActions"
          @busy="markChatBusy"
          @activity="refreshActivity"
          @inspect="openRun"
        />
      </div>
      <section v-if="workspaceTab === '运行记录'" class="aw-page">
        <div class="aw-row aw-between">
          <h2>{{ text("运行记录") }}</h2>
          <button class="aw-link" @click="loadRuns">刷新</button>
        </div>
        <p v-if="!current" class="aw-empty">{{ text("保存智能体后查看运行记录。") }}</p>
        <p v-else-if="runsLoading" class="aw-empty">{{ text("正在加载运行记录…") }}</p>
        <p v-else-if="!runs.length" class="aw-empty">
          {{ text("暂无运行记录，完成对话调试后可查看执行过程。") }}
        </p>
        <div v-else class="aw-table-wrap">
          <table class="aw-table">
            <thead>
              <tr>
                <th>{{ text("业务问题") }}</th>
                <th>{{ text("运行时间") }}</th>
                <th>{{ text("状态") }}</th>
                <th>{{ text("操作") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in runs" :key="run.id">
                <td>{{ run.question }}</td>
                <td>{{ formatTime(run.started_at) }}</td>
                <td>
                  <span
                    class="aw-pill"
                    :class="
                      ['error', 'failed', 'cancelled', 'pending_confirmation'].includes(run.status)
                        ? 'aw-amber'
                        : 'aw-green'
                    "
                    >{{ runStatus(run.status) }}</span
                  >
                </td>
                <td><button class="aw-link" @click="openRun(run.id)">{{ text("查看过程") }}</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section v-if="workspaceTab === '发布与接入'" class="aw-page">
        <div class="aw-two">
          <section>
            <h2>{{ text("已发布版本") }}</h2>
            <div class="aw-card">
              <strong>{{
                current?.current_version ? `v${current.current_version}` : text('尚未发布')
              }}</strong>
              <p class="aw-muted">{{ text("发布时固定模型、行为指引、本体版本、技能版本与动作策略。") }}</p>
            </div>
            <h2 v-if="publishedSnapshot" class="aw-section-title">{{ text("在线依赖快照") }}</h2>
            <dl v-if="publishedSnapshot" class="aw-info">
              <dt>{{ text("本体版本") }}</dt>
              <dd>{{ snapshotOntologyName }} · {{ snapshotVersionLabel }}</dd>
              <dt>{{ text("业务技能") }}</dt>
              <dd>
                <div v-for="binding in publishedBindings" :key="binding.skill_id">
                  {{ skillName(binding.skill_id) }} v{{ binding.version }}
                </div>
              </dd>
              <dt>{{ text("动作策略") }}</dt>
              <dd>
                {{
                  publishedSnapshot.tools_config?.action_mode === 'confirm'
                    ? text('执行前授权确认')
                    : text('模拟执行')
                }}
              </dd>
            </dl>
          </section>
          <section>
            <h2>接入方式</h2>
            <div v-if="!current?.current_version || current.status !== 'published'" class="aw-card">
              <strong>{{ current?.current_version ? '应用已下线' : text('发布后可接入') }}</strong>
              <p class="aw-muted">{{ text("完成配置与调试，发布业务应用后查看调用信息。") }}</p>
            </div>
            <p v-else-if="!canEdit" class="aw-muted">
              {{ text("查看应用密钥与接入示例需要配置写入权限。") }}
            </p>
            <template v-else
              ><div v-if="apiLoading" class="aw-muted">{{ text("正在读取接入信息…") }}</div>
              <div v-else-if="apiInfo" class="aw-card">
                <h3>应用 API</h3>
                <code class="aw-code">POST {{ apiInfo.endpoint }}</code
                ><button class="aw-link" @click="copyApi">{{ text("复制调用示例") }}</button>
                <details>
                  <summary>{{ text("查看调用示例（包含应用密钥）") }}</summary>
                  <pre>{{ apiInfo.curl }}</pre>
                </details>
              </div>
              <button
                class="aw-link aw-danger"
                :disabled="saving || !canEdit"
                @click="unpublishAgent"
              >
                {{ text("下线应用") }}
              </button></template
            >
          </section>
        </div>
        <div class="aw-row aw-between aw-section-title">
          <h2>{{ text("版本历史") }}</h2>
          <button class="aw-link" @click="loadVersions">刷新</button>
        </div>
        <p v-if="versionsLoading" class="aw-muted">{{ text("正在读取版本…") }}</p>
        <p v-else-if="!versions.length" class="aw-empty aw-empty-compact">{{ text("尚无发布版本。") }}</p>
        <div v-for="version in versions" :key="version.id" class="aw-version-row">
          <div>
            <strong>v{{ version.version }}</strong>
            <p class="aw-muted">
              {{ version.description || text('发布快照') }} · {{ formatTime(version.published_at) }}
            </p>
          </div>
          <button
            v-if="version.version !== current?.current_version"
            class="aw-link"
            :disabled="saving || !canEdit"
            @click="rollback(version)"
          >
            {{ text("回滚到此版本") }}</button
          ><span v-else class="aw-pill aw-green">{{ text("当前版本") }}</span>
        </div>
      </section>
    </template>
    <Teleport to="body"
      ><div
        v-if="drawer"
        class="aw-overlay"
        @click.self="drawer = null"
        @keydown.esc="drawer = null"
      >
        <section class="aw-drawer" role="dialog" aria-modal="true" :aria-label="drawerTitle">
          <header class="aw-row aw-between">
            <h2>{{ drawerTitle }}</h2>
            <button class="aw-icon" :aria-label="text('关闭')" @click="drawer = null">×</button>
          </header>
          <template v-if="drawer === 'skills'"
            ><p class="aw-muted">
              {{ text("选择可访问的已发布技能，固定版本后挂载。依赖必须在当前本体和对象范围内。") }}
            </p>
            <p v-if="drawerLoading" class="aw-empty">{{ text("正在检查技能版本依赖…") }}</p>
            <p v-else-if="!skillCandidates.length" class="aw-empty">{{ text("没有可访问的已发布技能。") }}</p>
            <article v-for="candidate in skillCandidates" :key="candidate.skill.id" class="aw-card">
              <div class="aw-row">
                <input
                  v-model="candidate.selected"
                  type="checkbox"
                  :aria-label="`挂载${candidate.skill.name}`"
                  :disabled="
                    candidate.problems.length > 0 ||
                    form.skill_bindings.some((b) => b.skill_id === candidate.skill.id)
                  "
                />
                <h3>{{ candidate.skill.name }}</h3>
              </div>
              <p class="aw-muted">{{ candidate.skill.description }}</p>
              <label class="aw-field"
                ><span>{{ text("固定发布版本") }}</span
                ><select
                  v-model.number="candidate.version"
                  @change="loadCandidateVersion(candidate)"
                >
                  <option
                    v-for="version in candidate.versions"
                    :key="version.version"
                    :value="version.version"
                  >
                    v{{ version.version }}
                  </option>
                </select></label
              >
              <p v-for="problem in candidate.problems" :key="problem" class="aw-text-error">
                {{ problem }}
              </p>
              <span v-if="!candidate.problems.length" class="aw-pill aw-green">{{ text("依赖匹配") }}</span
              ><span
                v-if="form.skill_bindings.some((b) => b.skill_id === candidate.skill.id)"
                class="aw-pill"
                >{{ text("已挂载") }}</span
              >
            </article>
            <footer class="aw-drawer-footer">
              <button
                class="aw-button aw-primary"
                :disabled="
                  drawerLoading || !skillCandidates.some((c) => c.selected && !c.problems.length)
                "
                @click="attachSkills"
              >
                {{ text("添加选中技能") }}
              </button>
            </footer></template
          >
          <template v-else-if="drawer === 'upgrade'"
            ><p class="aw-muted">{{ text("升级技能不会自动改变在线应用。保存并调试草稿后重新发布。") }}</p>
            <p v-if="drawerLoading" class="aw-empty">{{ text("正在读取版本变更…") }}</p>
            <template v-else-if="upgrade"
              ><h3>
                {{ upgrade.skill.name }} · v{{ upgrade.from.version }} → v{{ upgrade.to.version }}
              </h3>
              <div class="aw-two">
                <section>
                  <h3>{{ text("当前版本") }}</h3>
                  <p>{{ upgrade.from.description }}</p>
                  <pre>{{ upgrade.from.prompt_template }}</pre>
                  <details>
                    <summary>{{ text("输入、输出与依赖") }}</summary>
                    <pre>{{ JSON.stringify(upgradeDependencies(upgrade.from), null, 2) }}</pre>
                  </details>
                </section>
                <section>
                  <h3>{{ text("目标版本") }}</h3>
                  <p>{{ upgrade.to.description }}</p>
                  <pre>{{ upgrade.to.prompt_template }}</pre>
                  <details>
                    <summary>{{ text("输入、输出与依赖") }}</summary>
                    <pre>{{ JSON.stringify(upgradeDependencies(upgrade.to), null, 2) }}</pre>
                  </details>
                </section>
              </div>
              <p v-for="problem in upgrade.problems" :key="problem" class="aw-text-error">
                {{ problem }}
              </p>
              <footer class="aw-drawer-footer">
                <button
                  class="aw-button aw-primary"
                  :disabled="!!upgrade.problems.length"
                  @click="applyUpgrade"
                >
                  {{ text("使用目标版本") }}
                </button>
              </footer></template
            ></template
          >
          <template v-else-if="drawer === 'publish'"
            ><p class="aw-muted">{{ text("发布业务应用配置，固定本体、技能与执行策略。") }}</p>
            <div class="aw-card">
              <strong>{{ form.name }} · {{ form.skill_bindings.length }} 项技能</strong>
              <p>
                {{ selectedOntology?.name || '尚未选择本体' }} ·
                {{ selectedVersion ? `v${selectedVersion.version_number}` : '尚未选择版本' }}
              </p>
            </div>
            <div class="aw-publish-check">
              <span>草稿配置</span
              ><span class="aw-pill" :class="isDirty ? 'aw-amber' : 'aw-green'">{{
                isDirty ? '待保存' : text('已保存')
              }}</span>
            </div>
            <div class="aw-publish-check">
              <span>联合调试</span
              ><span class="aw-pill" :class="testPassed ? 'aw-green' : 'aw-amber'">{{
                testPassed ? '通过' : '待验证'
              }}</span>
            </div>
            <div class="aw-publish-check">
              <span>{{ text("执行策略") }}</span
              ><span class="aw-pill">{{
                form.action_mode === 'confirm' ? text('执行前授权确认') : text('模拟执行')
              }}</span>
            </div>
            <p v-for="problem in publishProblems" :key="problem" class="aw-text-error">
              {{ problem }}
            </p>
            <footer class="aw-drawer-footer">
              <button
                class="aw-button aw-primary"
                :disabled="publishing || publishProblems.length > 0"
                @click="publishAgent"
              >
                {{ publishing ? text('发布中…') : text('确认发布') }}
              </button>
            </footer></template
          >
          <template v-else-if="drawer === 'run'"
            ><p v-if="drawerLoading" class="aw-empty">{{ text("正在读取运行详情…") }}</p>
            <template v-else-if="selectedRun"
              ><h3>{{ selectedRun.question }}</h3>
              <p>{{ runStatus(selectedRun.status) }} · {{ formatTime(selectedRun.started_at) }}</p>
              <div v-if="selectedRun.error" class="aw-alert aw-error">{{ selectedRun.error }}</div>
              <div class="aw-markdown" v-html="renderMarkdownSafe(selectedRun.answer || '')"></div>
              <details
                v-for="(step, index) in selectedRun.steps || selectedRun.tool_runs || []"
                :key="index"
                class="aw-card"
              >
                <summary>{{ step.label || step.tool }} · {{ step.summary }}</summary>
                <pre>{{ JSON.stringify(step, null, 2) }}</pre>
              </details>
              <h3 v-if="selectedRun.pending_actions?.length">业务动作</h3>
              <article
                v-for="pending in selectedRun.pending_actions || []"
                :key="pending.pending_id"
                class="aw-card"
              >
                <strong>{{ pending.action_name }}</strong>
                <p>{{ pending.summary }}</p>
                <pre>{{ JSON.stringify(pending.params, null, 2) }}</pre>
                <p>{{ text('状态') }}：{{ runStatus(pending.status || 'pending') }}</p>
                <pre v-if="pending.result">{{ JSON.stringify(pending.result, null, 2) }}</pre>
                <div v-if="!pending.status || pending.status === 'pending'" class="aw-row">
                  <button
                    class="aw-button aw-primary"
                    :disabled="!!deciding || !canConfirmActions"
                    @click="decideRunAction(pending.pending_id, true)"
                  >
                    {{ text("授权并执行") }}</button
                  ><button
                    class="aw-button"
                    :disabled="!!deciding || !canConfirmActions"
                    @click="decideRunAction(pending.pending_id, false)"
                  >
                    {{ text("拒绝执行") }}
                  </button>
                </div>
              </article></template
            ></template
          >
          <p v-if="drawerError" class="aw-alert aw-error" role="alert">{{ drawerError }}</p>
        </section>
      </div></Teleport
    >
  </div>
</template>

<script setup lang="ts">
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()

import { formatPlatformDateTime } from '../../utils/platformTime'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import {
  agentsApi,
  modelsApi,
  type AgentItem,
  type AgentRun,
  type AgentSkillBinding,
  type AgentVersion,
  type ApiInfo,
  type ModelRegistry,
} from '../../api/agents'
import { ontologyPublishApi } from '../../api/ontologyPublish'
import {
  skillsApi,
  skillError,
  type SkillCatalog,
  type SkillCatalogItem,
  type SkillItem,
  type SkillVersion,
} from '../../api/skills'
import { copyText } from '../../utils/markdownExport'
import { renderMarkdownSafe } from '../../utils/sanitize'
import AgentChatPanel from './components/AgentChatPanel.vue'
import { useAuthStore } from '../../store/auth'

interface OntologyVersion {
  id: string
  version_number: string
  name: string
  status: string
  is_active: boolean
}
interface PublishedOntology {
  ontology_id: string
  code: string
  name: string
  active_version?: OntologyVersion
  versions: OntologyVersion[]
}
interface PinnedSkill extends SkillItem {
  version: number
}
interface Candidate {
  skill: SkillItem
  version: number
  versions: SkillVersion[]
  snapshot: PinnedSkill | null
  selected: boolean
  problems: string[]
}
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const canEdit = computed(() => authStore.hasPermission('rule:write'))
const canAuthorize = computed(() => authStore.hasPermission('strategy:execute') || authStore.hasPermission('rule:write'))
const canConfirmActions = computed(() => authStore.hasPermission('rule:execute') || authStore.hasPermission('rule:write'))
const workspaceTabs = ['配置与调试', '运行记录', '发布与接入'] as const
const configTabs = ['基本设置', '本体与能力', '行为规则'] as const
const workspaceTab = ref<(typeof workspaceTabs)[number]>('配置与调试')
const configTab = ref<(typeof configTabs)[number]>('基本设置')
const current = ref<AgentItem | null>(null)
const loading = ref(true)
const saving = ref(false)
const publishing = ref(false)
const chatBusy = ref(false)
const error = ref('')
const notice = ref('')
const ontologies = ref<PublishedOntology[]>([])
const models = ref<ModelRegistry[]>([])
const skills = ref<SkillItem[]>([])
const emptyCatalog = (): SkillCatalog => ({
  ontology_versions: [],
  entities: [],
  functions: [],
  actions: [],
  assets: [],
})
const catalog = ref<SkillCatalog>(emptyCatalog())
const catalogLoading = ref(false)
const pinned = reactive<Record<string, PinnedSkill>>({})
const pinErrors = reactive<Record<string, string>>({})
const form = reactive({
  name: '',
  description: '',
  tagsStr: '',
  model_id: '',
  system_prompt: '',
  ontology_id: '',
  ontology_version_id: '',
  entity_ids: [] as string[],
  skill_bindings: [] as AgentSkillBinding[],
  action_mode: 'simulation' as 'simulation' | 'confirm',
  max_tool_rounds: 12,
  execution_mode: 'react' as 'react' | 'graph',
  graph_json: '{"nodes": [], "edges": []}',
})
const savedSnapshot = ref('')
const versions = ref<AgentVersion[]>([])
const runs = ref<AgentRun[]>([])
const apiInfo = ref<ApiInfo | null>(null)
const versionsLoading = ref(false)
const runsLoading = ref(false)
const apiLoading = ref(false)
const selectedRun = ref<AgentRun | null>(null)
const deciding = ref('')
const drawer = ref<'skills' | 'upgrade' | 'publish' | 'run' | null>(null)
const drawerLoading = ref(false)
const drawerError = ref('')
const skillCandidates = ref<Candidate[]>([])
const upgrade = ref<{
  skill: SkillItem
  from: PinnedSkill
  to: PinnedSkill
  problems: string[]
} | null>(null)
let loadGeneration = 0
let catalogGeneration = 0
let runsRequest = 0
let versionsRequest = 0
let apiRequest = 0
let runRequest = 0
let savingNew = false
const activeModels = computed(() =>
  models.value.filter(
    (m) => m.status === 'active' && (!m.capabilities?.length || m.capabilities.includes('chat')),
  ),
)
const selectedOntology = computed(() =>
  ontologies.value.find((o) => o.ontology_id === form.ontology_id),
)
const ontologyVersions = computed(
  () =>
    selectedOntology.value?.versions.filter((v) => ['published', 'approved'].includes(v.status)) ||
    [],
)
const selectedVersion = computed(() =>
  ontologyVersions.value.find((v) => v.id === form.ontology_version_id),
)
function inSelectedObjectScope(item: SkillCatalogItem) {
  return (
    form.entity_ids.length > 0 &&
    (!item.entity_id || form.entity_ids.includes(String(item.entity_id)))
  )
}
const availableFunctions = computed(() => catalog.value.functions.filter(inSelectedObjectScope))
const availableActions = computed(() => catalog.value.actions.filter(inSelectedObjectScope))
const graphActionId = ref('')
const parsedGraph = computed(() => { try { return JSON.parse(form.graph_json) } catch { return null } })
const graphProblem = computed(() => {
  if (form.execution_mode !== 'graph') return ''
  const graph = parsedGraph.value
  if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) return '图定义必须是包含 nodes 和 edges 数组的有效 JSON。'
  if (!graph.nodes.length) return '图至少需要一个节点。'
  const ids = graph.nodes.map((node: any) => node.id)
  if (ids.some((id: any) => typeof id !== 'string' || !id) || new Set(ids).size !== ids.length) return '节点 ID 不能为空或重复。'
  if (graph.edges.some((edge: any) => !ids.includes(edge.source) || !ids.includes(edge.target))) return '连线两端必须引用已存在节点。'
  for (const node of graph.nodes) {
    const data = node.data || {}
    if (['action', 'human-approval'].includes(node.type) && !availableActions.value.some(action => action.id === data.action_id)) return `节点 ${node.id} 需要当前本体发布版本中的动作 action_id。`
    if (node.type === 'function' && !availableFunctions.value.some(fn => fn.id === data.function_id)) return `节点 ${node.id} 需要当前本体发布版本中的函数 function_id。`
  }
  return ''
})
function setApprovalGraph() {
  form.graph_json = JSON.stringify({ nodes: [
    { id: 'input', type: 'input', data: {} },
    { id: 'approval', type: 'human-approval', data: { action_id: graphActionId.value, params: {} } },
    { id: 'output', type: 'output', data: {} },
  ], edges: [{ source: 'input', target: 'approval' }, { source: 'approval', target: 'output' }] }, null, 2)
}
const isNew = computed(() => route.name === 'agent-new')
const isDirty = computed(() => JSON.stringify(payload()) !== savedSnapshot.value)
const testPassed = computed(
  () => !chatBusy.value && !isDirty.value && current.value?.last_test?.passed === true,
)
const drawerTitle = computed(
  () =>
    (
      ({
        skills: '添加业务技能',
        upgrade: '检查技能升级',
        publish: '发布智能体',
        run: '运行详情',
      }) as Record<string, string>
    )[drawer.value || ''] ? text(({skills:'添加业务技能',upgrade:'检查技能升级',publish:'发布智能体',run:'运行详情'} as Record<string,string>)[drawer.value || '']) : '',
)
const publishedSnapshot = computed(
  () => versions.value.find((v) => v.version === current.value?.current_version)?.config_snapshot,
)
const publishedBindings = computed<AgentSkillBinding[]>(
  () =>
    publishedSnapshot.value?.skill_bindings ||
    publishedSnapshot.value?.tools_config?.skill_bindings ||
    [],
)
const snapshotOntologyName = computed(
  () =>
    ontologies.value.find(
      (o) =>
        o.ontology_id ===
        (publishedSnapshot.value?.ontology_id ||
          publishedSnapshot.value?.tools_config?.ontology_id),
    )?.name || '本体',
)
const snapshotVersionLabel = computed(() => {
  const id =
    publishedSnapshot.value?.ontology_version_id ||
    publishedSnapshot.value?.tools_config?.ontology_version_id
  const version = ontologies.value.flatMap((o) => o.versions).find((v) => v.id === id)
  return version ? `v${version.version_number} · ${version.name}` : '原版本不可访问'
})
const publishProblems = computed(() => {
  const problems: string[] = []
  if (!current.value) problems.push('请先保存智能体。')
  if (!form.name.trim()) problems.push('请填写智能体名称。')
  if (isDirty.value) problems.push('配置已修改，请保存草稿。')
  if (!selectedVersion.value) problems.push('请选择可用的已发布本体版本。')
  if (!form.entity_ids.length) problems.push('请选择可访问的对象范围。')
  if (form.model_id && !activeModels.value.some((m) => m.id === form.model_id))
    problems.push('当前模型已停用或不可访问。')
  for (const binding of form.skill_bindings)
    problems.push(...bindingProblems(binding).map((p) => `${skillName(binding.skill_id)}：${p}`))
  if (graphProblem.value) problems.push(graphProblem.value)
  if (!testPassed.value) problems.push('当前草稿尚未通过联合调试。')
  return problems
})
function payload(): Partial<AgentItem> {
  return {
    name: form.name.trim(),
    description: form.description,
    tags: form.tagsStr
      .split(/[,，]/)
      .map((t) => t.trim())
      .filter(Boolean),
    model_id: form.model_id || null,
    system_prompt: form.system_prompt,
    entity_ids: [...form.entity_ids],
    nodes_json: form.execution_mode === 'graph' ? (parsedGraph.value?.nodes || []) : [],
    edges_json: form.execution_mode === 'graph' ? (parsedGraph.value?.edges || []) : [],
    tools_config: {
      ...(current.value?.tools_config || {}),
      ontology_id: form.ontology_id || null,
      ontology_version_id: form.ontology_version_id || null,
      skill_bindings: form.skill_bindings.map((b) => ({ ...b })),
      action_mode: form.action_mode,
      max_tool_rounds: form.max_tool_rounds,
    },
  }
}
function hydrate(agent: AgentItem) {
  current.value = agent
  const config = agent.tools_config || {}
  Object.assign(form, {
    name: agent.name || '',
    description: agent.description || '',
    tagsStr: (agent.tags || []).join(', '),
    model_id: agent.model_id || '',
    system_prompt: agent.system_prompt || '',
    ontology_id: agent.ontology_id || config.ontology_id || '',
    ontology_version_id: agent.ontology_version_id || config.ontology_version_id || '',
    entity_ids: [...(agent.entity_ids || [])],
    skill_bindings: (agent.skill_bindings || config.skill_bindings || []).map(
      (b: AgentSkillBinding) => ({ ...b }),
    ),
    action_mode: config.action_mode === 'confirm' ? 'confirm' : 'simulation',
    max_tool_rounds: config.max_tool_rounds || 12,
    execution_mode: agent.nodes_json?.length ? 'graph' : 'react',
    graph_json: JSON.stringify({ nodes: agent.nodes_json || [], edges: agent.edges_json || [] }, null, 2),
  })
  savedSnapshot.value = JSON.stringify(payload())
}
function entitySourceId(entity: SkillCatalogItem) {
  return String(entity.source_entity_id || entity.id)
}
function skillName(id: string) {
  return skills.value.find((s) => s.id === id)?.name || '不可访问的技能'
}
function pinKey(binding: AgentSkillBinding) {
  return `${binding.skill_id}:${binding.version}`
}
function boundSkill(binding: AgentSkillBinding) {
  return pinned[pinKey(binding)]
}
function latestSkillVersion(id: string) {
  return skills.value.find((s) => s.id === id)?.current_version || 0
}
function snapshotProblems(snapshot: PinnedSkill | null) {
  if (!snapshot) return ['无法读取已发布技能版本。']
  const problems: string[] = []
  if (snapshot.ontology_id !== form.ontology_id) problems.push('本体范围不匹配。')
  if (snapshot.ontology_version_id !== form.ontology_version_id)
    problems.push('技能固定的本体版本与当前版本不一致。')
  if ((snapshot.entity_ids || []).some((id) => !form.entity_ids.includes(id)))
    problems.push('技能依赖对象不在授权范围内。')
  if (
    (snapshot.tools || []).some(
      (t) =>
        !(t.type === 'action' ? catalog.value.actions : catalog.value.functions).some(
          (item) => item.id === t.id,
        ),
    )
  )
    problems.push('依赖逻辑或动作在本体版本中不可用。')
  if (
    (snapshot.asset_refs || []).some((id) => !catalog.value.assets.some((item) => item.id === id))
  )
    problems.push('依赖资料不可访问。')
  return problems
}
function bindingProblems(binding: AgentSkillBinding) {
  const skill = skills.value.find((s) => s.id === binding.skill_id)
  if (pinErrors[pinKey(binding)]) return [pinErrors[pinKey(binding)]!]
  if (!skill || skill.status !== 'active') return ['技能已归档或不可访问。']
  if (!boundSkill(binding)) return ['正在读取固定版本…']
  return snapshotProblems(boundSkill(binding))
}
async function fetchPinned(id: string, version: number): Promise<PinnedSkill> {
  const result = await skillsApi.version(id, version)
  const snapshot = result.snapshot_json || result.snapshot || result.definition
  if (!snapshot) throw new Error(text('发布版本未提供依赖快照'))
  const value = { ...snapshot, version }
  pinned[`${id}:${version}`] = value
  delete pinErrors[`${id}:${version}`]
  return value
}
async function loadPins() {
  await Promise.all(
    form.skill_bindings.map(async (binding) => {
      try {
        await fetchPinned(binding.skill_id, binding.version)
      } catch (e) {
        pinErrors[pinKey(binding)] = skillError(e)
      }
    }),
  )
}
async function loadCatalog() {
  const generation = ++catalogGeneration
  catalog.value = emptyCatalog()
  catalogLoading.value = false
  if (!form.ontology_id || !form.ontology_version_id) return
  catalogLoading.value = true
  try {
    const result = await skillsApi.catalog(form.ontology_id, form.ontology_version_id)
    if (generation === catalogGeneration) catalog.value = result
  } catch (e) {
    if (generation === catalogGeneration) error.value = skillError(e)
  } finally {
    if (generation === catalogGeneration) catalogLoading.value = false
  }
}
async function changeOntology() {
  form.ontology_version_id = ''
  form.entity_ids = []
  form.skill_bindings = []
  await loadCatalog()
}
async function changeOntologyVersion() {
  form.entity_ids = []
  await loadCatalog()
}
async function saveAgent() {
  if (saving.value || chatBusy.value || !canEdit.value) return
  if (!isNew.value && !current.value) {
    error.value = text('智能体尚未加载，请刷新后重试。')
    return
  }
  if (!form.name.trim()) {
    error.value = text('请填写智能体名称。')
    configTab.value = '基本设置'
    return
  }
  if (
    !Number.isInteger(form.max_tool_rounds) ||
    form.max_tool_rounds < 2 ||
    form.max_tool_rounds > 20
  ) {
    error.value = text('工具调用轮次应为 2–20。')
    return
  }
  if (graphProblem.value) { error.value = graphProblem.value; return }
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const data = payload()
    const result = current.value
      ? await agentsApi.update(current.value.id, data)
      : await agentsApi.create(data)
    hydrate(result)
    notice.value = text('草稿已保存，请调试验证当前配置。')
    if (isNew.value) {
      savingNew = true
      await router.replace(`/agent/manage/${result.id}`)
      savingNew = false
    }
  } catch (e) {
    error.value = skillError(e)
  } finally {
    saving.value = false
    savingNew = false
  }
}
async function openSkillDrawer() {
  drawer.value = 'skills'
  drawerLoading.value = true
  drawerError.value = ''
  skillCandidates.value = []
  try {
    const candidates = await Promise.all(
      skills.value
        .filter((s) => s.status === 'active' && s.current_version > 0)
        .map(async (skill) => {
          const versions = await skillsApi.versions(skill.id)
          const candidate: Candidate = {
            skill,
            versions,
            version: skill.current_version,
            snapshot: null,
            selected: false,
            problems: [],
          }
          try {
            candidate.snapshot = await fetchPinned(skill.id, candidate.version)
            candidate.problems = snapshotProblems(candidate.snapshot)
          } catch (e) {
            candidate.problems = [skillError(e)]
          }
          return candidate
        }),
    )
    skillCandidates.value = candidates
  } catch (e) {
    drawerError.value = skillError(e)
  } finally {
    drawerLoading.value = false
  }
}
async function loadCandidateVersion(candidate: Candidate) {
  const requestedVersion = candidate.version
  candidate.selected = false
  candidate.problems = ['正在检查依赖…']
  try {
    const snapshot = await fetchPinned(candidate.skill.id, requestedVersion)
    if (candidate.version !== requestedVersion) return
    candidate.snapshot = snapshot
    candidate.problems = snapshotProblems(candidate.snapshot)
  } catch (e) {
    if (candidate.version === requestedVersion) candidate.problems = [skillError(e)]
  }
}
function upgradeDependencies(skill: PinnedSkill) {
  return {
    ontology_version_id: skill.ontology_version_id,
    entity_ids: skill.entity_ids,
    tools: skill.tools,
    asset_refs: skill.asset_refs,
    input_schema: skill.input_schema,
    output_schema: skill.output_schema,
  }
}
function attachSkills() {
  for (const c of skillCandidates.value)
    if (
      c.selected &&
      !c.problems.length &&
      !form.skill_bindings.some((b) => b.skill_id === c.skill.id)
    )
      form.skill_bindings.push({ skill_id: c.skill.id, version: c.version })
  drawer.value = null
}
function unmountSkill(binding: AgentSkillBinding) {
  if (
    window.confirm(`从当前草稿卸载「${skillName(binding.skill_id)}」？重新保存、调试和发布后生效。`)
  )
    form.skill_bindings = form.skill_bindings.filter((b) => b.skill_id !== binding.skill_id)
}
async function reviewUpgrade(binding: AgentSkillBinding) {
  drawer.value = 'upgrade'
  drawerError.value = ''
  drawerLoading.value = true
  upgrade.value = null
  try {
    const skill = skills.value.find((s) => s.id === binding.skill_id)!
    const [from, to] = await Promise.all([
      fetchPinned(binding.skill_id, binding.version),
      fetchPinned(binding.skill_id, skill.current_version),
    ])
    upgrade.value = { skill, from, to, problems: snapshotProblems(to) }
  } catch (e) {
    drawerError.value = skillError(e)
  } finally {
    drawerLoading.value = false
  }
}
function applyUpgrade() {
  if (!upgrade.value || upgrade.value.problems.length) return
  const binding = form.skill_bindings.find((b) => b.skill_id === upgrade.value!.skill.id)
  if (binding) binding.version = upgrade.value.to.version
  drawer.value = null
}
async function refreshActivity() {
  if (!current.value) return
  const id = current.value.id
  const generation = loadGeneration
  try {
    const latest = await agentsApi.get(id)
    if (generation !== loadGeneration || current.value?.id !== id) return
    current.value = latest
    if (workspaceTab.value === '运行记录') await loadRuns()
  } catch (e) {
    if (generation === loadGeneration) error.value = skillError(e)
  }
}
function markChatBusy(value: boolean) {
  chatBusy.value = value
  if (value && current.value) current.value.last_test = null
}
async function loadRuns() {
  if (!current.value) return
  const id = current.value.id
  const request = ++runsRequest
  const generation = loadGeneration
  runsLoading.value = true
  try {
    const result = await agentsApi.runs(id)
    if (request === runsRequest && generation === loadGeneration) runs.value = result
  } catch (e) {
    if (request === runsRequest && generation === loadGeneration) error.value = skillError(e)
  } finally {
    if (request === runsRequest && generation === loadGeneration) runsLoading.value = false
  }
}
async function loadVersions() {
  if (!current.value) return
  const id = current.value.id
  const request = ++versionsRequest
  const generation = loadGeneration
  versionsLoading.value = true
  try {
    const result = await agentsApi.versions(id)
    if (request === versionsRequest && generation === loadGeneration) versions.value = result
  } catch (e) {
    if (request === versionsRequest && generation === loadGeneration) error.value = skillError(e)
  } finally {
    if (request === versionsRequest && generation === loadGeneration) versionsLoading.value = false
  }
}
async function loadApi() {
  const request = ++apiRequest
  const generation = loadGeneration
  apiInfo.value = null
  apiLoading.value = false
  if (!canEdit.value) return
  if (!current.value?.current_version || current.value.status !== 'published') return
  const id = current.value.id
  apiLoading.value = true
  try {
    const result = await agentsApi.apiInfo(id)
    if (request === apiRequest && generation === loadGeneration) apiInfo.value = result
  } catch (e) {
    if (request === apiRequest && generation === loadGeneration) error.value = skillError(e)
  } finally {
    if (request === apiRequest && generation === loadGeneration) apiLoading.value = false
  }
}
async function selectWorkspaceTab(tab: (typeof workspaceTabs)[number]) {
  workspaceTab.value = tab
  if (tab === '运行记录') await loadRuns()
  if (tab === '发布与接入') await Promise.all([loadVersions(), loadApi()])
}
async function publishAgent() {
  if (publishing.value || saving.value || !current.value || publishProblems.value.length) return
  publishing.value = true
  drawerError.value = ''
  try {
    const result = await agentsApi.publish(current.value.id)
    hydrate(result)
    drawer.value = null
    notice.value = `智能体 v${result.current_version} 已发布。`
    await Promise.all([loadVersions(), loadApi()])
  } catch (e) {
    drawerError.value = skillError(e)
  } finally {
    publishing.value = false
  }
}
async function unpublishAgent() {
  if (
    saving.value ||
    publishing.value ||
    !current.value ||
    !window.confirm(text('下线后外部应用将无法调用此智能体，确认下线？'))
  )
    return
  saving.value = true
  try {
    current.value = await agentsApi.update(current.value.id, { status: 'draft' })
    apiInfo.value = null
    notice.value = text('应用已下线。')
  } catch (e) {
    error.value = skillError(e)
  } finally {
    saving.value = false
  }
}
async function rollback(version: AgentVersion) {
  if (
    saving.value ||
    publishing.value ||
    !current.value ||
    !window.confirm(
      `回滚到 v${version.version}？${isDirty.value ? '当前未保存修改将被替换。' : ''}`,
    )
  )
    return
  saving.value = true
  try {
    hydrate(await agentsApi.rollback(current.value.id, version.version))
    await Promise.all([loadCatalog(), loadPins(), loadVersions(), loadApi()])
    notice.value = `已回滚到 v${version.version}。`
  } catch (e) {
    error.value = skillError(e)
  } finally {
    saving.value = false
  }
}
async function copyApi() {
  if (apiInfo.value && !(await copyText(apiInfo.value.curl)))
    error.value = text('复制失败，请手动复制调用示例。')
}
async function openRun(id: string) {
  if (deciding.value || !current.value) return
  const request = ++runRequest
  const generation = loadGeneration
  const agentId = current.value.id
  drawer.value = 'run'
  drawerLoading.value = true
  drawerError.value = ''
  selectedRun.value = null
  try {
    const result = await agentsApi.run(agentId, id)
    if (request === runRequest && generation === loadGeneration) selectedRun.value = result
  } catch (e) {
    if (request === runRequest && generation === loadGeneration) drawerError.value = skillError(e)
  } finally {
    if (request === runRequest && generation === loadGeneration) drawerLoading.value = false
  }
}
async function decideRunAction(pendingId: string, approve: boolean) {
  if (!canConfirmActions.value || deciding.value || !current.value || !selectedRun.value) return
  const agentId = current.value.id
  const runId = selectedRun.value.id
  const generation = loadGeneration
  deciding.value = pendingId
  try {
    await agentsApi.confirmAction(agentId, pendingId, approve)
    const result = await agentsApi.run(agentId, runId)
    if (generation !== loadGeneration) return
    selectedRun.value = result
    await loadRuns()
  } catch (e) {
    drawerError.value = skillError(e)
  } finally {
    deciding.value = ''
  }
}
function runStatus(status: string) {
  return text(
    (
      {
        ok: '完成',
        completed: '完成',
        success: '完成',
        error: '失败',
        failed: '失败',
        running: '运行中',
        pending: '等待授权',
        pending_action: '等待授权',
        pending_confirmation: '等待授权',
        approved: '已授权执行',
        rejected: '已拒绝执行',
        expired: '授权已过期',
        executing: '行动正在执行',
        cancelled: '已中止',
        partial_committed: '部分写入已提交，已完成写入保留；请核查回执，原行动不可重试',
      } as Record<string, string>
    )[status] || status
  )
}
function formatTime(value?: string) {
  return formatPlatformDateTime(value)
}
watch(drawer, () => {
  drawerError.value = ''
})
watch(
  () => route.fullPath,
  async () => {
    if (savingNew) return
    const generation = ++loadGeneration
    catalogGeneration++
    runsRequest++
    versionsRequest++
    apiRequest++
    runRequest++
    loading.value = true
    error.value = ''
    notice.value = ''
    current.value = null
    drawer.value = null
    versions.value = []
    runs.value = []
    apiInfo.value = null
    selectedRun.value = null
    runsLoading.value = false
    versionsLoading.value = false
    apiLoading.value = false
    drawerLoading.value = false
    chatBusy.value = false
    catalog.value = emptyCatalog()
    workspaceTab.value = '配置与调试'
    configTab.value = isNew.value ? '基本设置' : '本体与能力'
    Object.assign(form, {
      name: '',
      description: '',
      tagsStr: '',
      model_id: '',
      system_prompt: '',
      ontology_id: '',
      ontology_version_id: '',
      entity_ids: [],
      skill_bindings: [],
      action_mode: 'simulation',
      max_tool_rounds: 12,
      execution_mode: 'react',
      graph_json: '{"nodes": [], "edges": []}',
    })
    savedSnapshot.value = JSON.stringify(payload())
    try {
      if (!authStore.user) await authStore.fetchUser()
      const results = await Promise.allSettled([
        modelsApi.list(),
        ontologyPublishApi.listPublishedOntologies(),
        skillsApi.list(),
        isNew.value ? Promise.resolve(null) : agentsApi.get(String(route.params.id)),
      ])
      if (generation !== loadGeneration) return
      const [modelResult, ontologyResult, skillResult, agentResult] = results
      if (modelResult.status === 'fulfilled') models.value = modelResult.value
      else error.value = skillError(modelResult.reason)
      if (ontologyResult.status === 'fulfilled') ontologies.value = ontologyResult.value
      else error.value = skillError(ontologyResult.reason)
      if (skillResult.status === 'fulfilled') skills.value = skillResult.value
      else error.value = skillError(skillResult.reason)
      if (agentResult.status === 'fulfilled' && agentResult.value) {
        hydrate(agentResult.value)
        await Promise.all([loadCatalog(), loadPins()])
      } else if (agentResult.status === 'rejected') error.value = skillError(agentResult.reason)
      if (generation === loadGeneration) loading.value = false
    } catch (e) {
      if (generation === loadGeneration) {
        error.value = skillError(e, '智能体加载失败，请刷新重试')
        loading.value = false
      }
    }
  },
  { immediate: true },
)
onBeforeRouteLeave(() => {
  if (savingNew) return true
  if (saving.value || publishing.value || deciding.value) {
    error.value = text('操作正在进行，请等待完成后再离开。')
    return false
  }
  if (chatBusy.value) return window.confirm(text('离开页面将中止调试响应，确认离开？'))
  if (isDirty.value) return window.confirm(text('当前草稿尚未保存，确认离开？'))
})
onBeforeRouteUpdate(() => {
  if (!savingNew && (saving.value || publishing.value || deciding.value)) {
    error.value = text('操作正在进行，请等待完成后再切换智能体。')
    return false
  }
  if (!savingNew && (isDirty.value || chatBusy.value))
    return window.confirm(text('当前配置尚未保存或仍在调试，确认切换智能体？'))
})
onBeforeUnmount(() => {
  loadGeneration++
  catalogGeneration++
})
</script>
<style src="../../styles/agent-workbench.css"></style>
