<template>
  <div class="sk-page">
    <div class="sk-head">
      <div>
        <h1 class="sk-title">Skill 注册中心</h1>
        <p class="sk-sub">管理可被 Agent / AIP 场景调用的能力包</p>
      </div>
      <button class="sk-btn sk-btn--primary" @click="onCreate">+ 新建 Skill</button>
    </div>

    <div class="sk-toolbar">
      <input class="sk-input" v-model="keyword" placeholder="搜索 Skill 名称、描述、code_ref..." />
      <select class="sk-input sk-input--sm" v-model="typeFilter">
        <option value="">全部类型</option>
        <option value="builtin">builtin（内置）</option>
        <option value="llm">llm（LLM 驱动）</option>
        <option value="ml">ml（ML 模型）</option>
        <option value="custom">custom（自定义）</option>
      </select>
    </div>

    <div class="sk-grid">
      <div v-for="s in filtered" :key="s.id" class="sk-card" @click="onEdit(s)">
        <div class="sk-card__head">
          <div class="sk-card__name">{{ s.name }}</div>
          <span class="sk-tag" :class="`sk-tag--${s.status}`">{{ s.status }}</span>
        </div>
        <div class="sk-card__type">{{ s.skill_type }} · {{ s.code_ref || '—' }}</div>
        <p class="sk-card__desc">{{ s.description || '暂无描述' }}</p>
        <div class="sk-card__params" v-if="paramSummary(s)">
          <span class="sk-pill" v-for="p in paramSummary(s)" :key="p">{{ p }}</span>
        </div>
        <div class="sk-card__time">更新于 {{ formatTime(s.updated_at) }}</div>
      </div>
      <div v-if="!filtered.length" class="sk-empty">暂无 Skill — 点击右上角"新建"添加</div>
    </div>

    <!-- 编辑抽屉 -->
    <div v-if="editing" class="sk-mask" @click.self="editing = null">
      <div class="sk-drawer">
        <div class="sk-drawer__head">
          <span class="sk-drawer__title">{{ editing.id ? '编辑 Skill' : '新建 Skill' }}</span>
          <button class="sk-icon-btn" @click="editing = null">×</button>
        </div>
        <div class="sk-drawer__body">
          <div class="sk-field"><label>名称</label><input class="sk-input" v-model="editing.name" /></div>
          <div class="sk-field"><label>描述</label><textarea class="sk-input sk-input--ta" rows="3" v-model="editing.description"></textarea></div>
          <div class="sk-field"><label>类型</label>
            <select class="sk-input" v-model="editing.skill_type">
              <option value="builtin">builtin</option>
              <option value="llm">llm</option>
              <option value="ml">ml</option>
              <option value="custom">custom</option>
            </select>
          </div>
          <div class="sk-field"><label>code_ref（绑定后端实现的标识）</label><input class="sk-input" v-model="editing.code_ref" placeholder="如 mnp_risk_evaluate" /></div>
          <div class="sk-field"><label>参数 Schema (JSON)</label>
            <textarea class="sk-input sk-input--ta" rows="6" :value="JSON.stringify(editing.config_json || {}, null, 2)"
              @input="onConfigChange"></textarea>
          </div>
          <div class="sk-field"><label>状态</label>
            <select class="sk-input" v-model="editing.status">
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
          </div>
        </div>
        <div class="sk-drawer__foot">
          <button class="sk-btn sk-btn--danger" v-if="editing.id" @click="onDelete">删除</button>
          <div style="flex:1"></div>
          <button class="sk-btn" @click="editing = null">取消</button>
          <button class="sk-btn sk-btn--primary" @click="onSave">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { skillsApi, type SkillItem } from '../../api/skills'

const skills = ref<SkillItem[]>([])
const keyword = ref('')
const typeFilter = ref('')
const editing = ref<Partial<SkillItem> | null>(null)

async function reload() {
  try {
    skills.value = await skillsApi.list()
  } catch {
    skills.value = []
  }
}

onMounted(reload)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return skills.value.filter((s) => {
    if (typeFilter.value && s.skill_type !== typeFilter.value) return false
    if (!kw) return true
    return (
      s.name.toLowerCase().includes(kw) ||
      (s.description || '').toLowerCase().includes(kw) ||
      (s.code_ref || '').toLowerCase().includes(kw)
    )
  })
})

function paramSummary(s: SkillItem): string[] {
  const params = (s.config_json || {}).params || []
  if (!Array.isArray(params)) return []
  return params.slice(0, 4).map((p: any) => `${p.name}${p.required ? '*' : ''}: ${p.type || 'any'}`)
}

function formatTime(t: string): string {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

function onCreate() {
  editing.value = {
    name: '', description: '', skill_type: 'builtin', code_ref: '',
    config_json: { params: [] }, status: 'active',
  }
}
function onEdit(s: SkillItem) {
  editing.value = JSON.parse(JSON.stringify(s))
}
function onConfigChange(e: Event) {
  if (!editing.value) return
  const v = (e.target as HTMLTextAreaElement).value
  try {
    editing.value.config_json = v.trim() ? JSON.parse(v) : {}
  } catch {
    /* keep typing */
  }
}
async function onSave() {
  if (!editing.value) return
  try {
    if (editing.value.id) {
      await skillsApi.update(editing.value.id, editing.value)
    } else {
      await skillsApi.create(editing.value)
    }
    editing.value = null
    await reload()
  } catch (e) {
    window.alert(`保存失败: ${(e as Error).message}`)
  }
}
async function onDelete() {
  if (!editing.value?.id) return
  if (!window.confirm(`确定删除 Skill「${editing.value.name}」？`)) return
  await skillsApi.delete(editing.value.id)
  editing.value = null
  await reload()
}
</script>

<style scoped>
.sk-page { padding: 20px 24px; height: 100%; overflow: auto; background: var(--ao-bg-primary, #f5f7fb); }
.sk-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.sk-title { font-size: 20px; font-weight: 700; color: #1e293b; margin: 0; }
.sk-sub { font-size: 13px; color: #64748b; margin: 4px 0 0; }
.sk-toolbar { display: flex; gap: 8px; margin-bottom: 16px; }
.sk-input { width: 100%; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px; outline: none; background: #fff; }
.sk-input--sm { width: 200px; flex-shrink: 0; }
.sk-input--ta { resize: vertical; min-height: 80px; font-family: ui-monospace, monospace; }
.sk-input:focus { border-color: #2E5BFF; }

.sk-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.sk-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.sk-card:hover { border-color: #2E5BFF; box-shadow: 0 4px 12px rgba(46,91,255,.08); }
.sk-card__head { display: flex; align-items: center; justify-content: space-between; }
.sk-card__name { font-weight: 600; font-size: 14px; color: #1e293b; }
.sk-card__type { font-size: 11px; color: #64748b; margin-top: 4px; font-family: ui-monospace, monospace; }
.sk-card__desc { font-size: 12px; color: #475569; line-height: 1.5; margin: 8px 0 0; min-height: 36px; }
.sk-card__params { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.sk-card__time { font-size: 10px; color: #94a3b8; margin-top: 8px; }

.sk-tag { font-size: 10px; padding: 1px 8px; border-radius: 999px; }
.sk-tag--active { background: #ecfdf5; color: #059669; }
.sk-tag--inactive { background: #f1f5f9; color: #64748b; }
.sk-pill { font-size: 10px; padding: 1px 6px; background: #eff6ff; color: #2563eb; border-radius: 4px; font-family: ui-monospace, monospace; }

.sk-empty { grid-column: 1/-1; padding: 60px; text-align: center; color: #94a3b8; font-size: 13px; }

.sk-btn { display: inline-flex; align-items: center; padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 4px; background: #fff; color: #475569; cursor: pointer; font-size: 12px; }
.sk-btn:hover { border-color: #2E5BFF; color: #2E5BFF; }
.sk-btn--primary { background: #2E5BFF; color: #fff; border-color: #2E5BFF; }
.sk-btn--primary:hover { background: #1d4ed8; color: #fff; }
.sk-btn--danger { color: #ef4444; border-color: #fecaca; }
.sk-btn--danger:hover { background: #fef2f2; }

.sk-mask { position: fixed; inset: 0; background: rgba(15,23,42,.4); z-index: 100; display: flex; justify-content: flex-end; }
.sk-drawer { width: 480px; background: #fff; height: 100%; display: flex; flex-direction: column; }
.sk-drawer__head { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; justify-content: space-between; }
.sk-drawer__title { font-weight: 700; font-size: 14px; }
.sk-drawer__body { flex: 1; padding: 14px 18px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.sk-drawer__foot { padding: 12px 18px; border-top: 1px solid #f0f0f0; display: flex; gap: 8px; }
.sk-icon-btn { width: 28px; height: 28px; border: none; background: transparent; cursor: pointer; color: #94a3b8; font-size: 18px; border-radius: 4px; }
.sk-icon-btn:hover { background: #f1f5f9; color: #1e293b; }
.sk-field { display: flex; flex-direction: column; gap: 4px; }
.sk-field > label { font-size: 11px; color: #475569; font-weight: 500; }
</style>
