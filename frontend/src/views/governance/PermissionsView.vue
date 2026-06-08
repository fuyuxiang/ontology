<template>
  <div class="perm-page">
    <div class="perm-page__header">
      <div>
        <h1 class="perm-page__title">权限管理</h1>
        <p class="perm-page__subtitle">用户账号 · 角色配置 · 权限矩阵</p>
      </div>
    </div>

    <div class="perm-page__tabs">
      <button v-for="tab in tabs" :key="tab.key" class="perm-tab" :class="{ 'perm-tab--active': activeTab === tab.key }" @click="activeTab = tab.key">
        <span class="perm-tab__icon">{{ tab.icon }}</span>
        {{ tab.label }}
      </button>
    </div>

    <!-- ========== 用户管理 ========== -->
    <div v-if="activeTab === 'users'" class="perm-section">
      <div class="perm-section__toolbar">
        <a-input-search v-model:value="userKeyword" placeholder="搜索姓名或账号" style="width: 260px" allow-clear @search="fetchUsers" @change="(e: Event) => { if (!(e.target as HTMLInputElement).value) fetchUsers() }" />
        <a-select v-model:value="userRoleFilter" placeholder="全部角色" allow-clear style="width: 140px" :options="roleOptions" @change="fetchUsers" />
        <a-select v-model:value="userStatusFilter" placeholder="全部状态" allow-clear style="width: 120px" :options="[{label:'启用',value:true},{label:'禁用',value:false}]" @change="fetchUsers" />
        <button class="perm-btn perm-btn--primary" style="margin-left:auto" @click="openCreateUser">
          <span style="margin-right:4px">＋</span> 新增用户
        </button>
      </div>

      <table class="user-table" v-if="users.length">
        <thead><tr><th>姓名</th><th>账号</th><th>邮箱</th><th>角色</th><th>状态</th><th>最近登录</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="user-table__row">
            <td>
              <div class="user-table__name-cell">
                <span class="user-table__avatar" :class="`user-table__avatar--${u.role}`">{{ u.name[0] }}</span>
                <span class="user-table__name">{{ u.name }}</span>
              </div>
            </td>
            <td class="user-table__mono">{{ u.username }}</td>
            <td class="user-table__mono">{{ u.email || '-' }}</td>
            <td><span class="role-tag" :class="`role--${u.role}`">{{ roleLabel(u.role) }}</span></td>
            <td>
              <span class="status-dot" :class="u.is_active ? 'status-dot--on' : 'status-dot--off'"></span>
              {{ u.is_active ? '启用' : '禁用' }}
            </td>
            <td class="user-table__mono">{{ formatTime(u.last_login_at) }}</td>
            <td>
              <a-dropdown>
                <button class="perm-btn--icon">⋯</button>
                <template #overlay>
                  <a-menu @click="(info: any) => handleUserAction(info.key, u)">
                    <a-menu-item key="edit">编辑</a-menu-item>
                    <a-menu-item key="toggle">{{ u.is_active ? '禁用' : '启用' }}</a-menu-item>
                    <a-menu-item key="reset">重置密码</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!usersLoading" class="perm-empty">
        <div class="perm-empty__icon">👥</div>
        <p class="perm-empty__title">暂无用户</p>
        <p class="perm-empty__desc">点击「新增用户」添加第一个用户</p>
      </div>

      <div class="perm-pagination" v-if="usersTotal > 0">
        <span class="perm-pagination__total">共 {{ usersTotal }} 人</span>
        <a-pagination v-model:current="usersPage" :page-size="usersPageSize" :total="usersTotal" size="small" @change="fetchUsers" />
      </div>
    </div>

    <!-- ========== 角色管理 ========== -->
    <div v-if="activeTab === 'roles'" class="perm-section">
      <div class="role-grid">
        <div v-for="role in roles" :key="role.key" class="role-card" @click="openRoleDrawer(role)">
          <div class="role-card__header">
            <div class="role-card__icon" :class="`role-card__icon--${role.key}`">{{ roleIcon(role.key) }}</div>
            <span v-if="role.is_system" class="role-card__system-tag">系统</span>
          </div>
          <div class="role-card__name">{{ role.label }}</div>
          <div class="role-card__desc">{{ role.description }}</div>
          <div class="role-card__stats">
            <span>👤 {{ role.user_count }}人</span>
            <span>🔑 {{ role.permissions.length }}项权限</span>
          </div>
          <button class="role-card__edit-btn" @click.stop="openRoleDrawer(role)">编辑权限</button>
        </div>
      </div>
    </div>

    <!-- ========== 权限矩阵 ========== -->
    <div v-if="activeTab === 'matrix'" class="perm-section">
      <div class="matrix-header">
        <p class="matrix-header__hint">点击单元格可切换权限级别</p>
        <button v-if="matrixChanged" class="perm-btn perm-btn--primary" @click="handleSaveMatrix" :disabled="savingMatrix">
          {{ savingMatrix ? '保存中...' : '保存变更' }}
        </button>
      </div>
      <div class="matrix-wrap">
        <table class="matrix-table">
          <thead>
            <tr>
              <th class="matrix-table__corner">角色</th>
              <template v-for="mod in modules" :key="mod.key">
                <th :colspan="mod.permissions.length" class="matrix-table__group-th">{{ mod.label }}</th>
              </template>
            </tr>
            <tr>
              <th></th>
              <template v-for="mod in modules" :key="mod.key">
                <th v-for="p in mod.permissions" :key="p" class="matrix-table__sub-th">{{ permLabel(p) }}</th>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr v-for="role in roles" :key="role.key" class="matrix-table__row">
              <td class="matrix-table__role">
                <span class="matrix-table__role-icon">{{ roleIcon(role.key) }}</span>
                {{ role.label }}
              </td>
              <template v-for="mod in modules" :key="mod.key">
                <td
                  v-for="p in mod.permissions"
                  :key="p"
                  class="matrix-table__cell"
                  :class="[getCellClass(getRolePerms(role.key), p), { 'matrix-table__cell--changed': isCellChanged(role.key, p) }]"
                  @click="cyclePerm(role.key, p)"
                >
                  {{ getPermSymbol(getRolePerms(role.key), p) }}
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="matrix-legend">
        <span class="matrix-legend__item"><span class="matrix-legend__icon matrix-legend__icon--manage">■</span> 管理</span>
        <span class="matrix-legend__item"><span class="matrix-legend__icon matrix-legend__icon--write">◧</span> 读写</span>
        <span class="matrix-legend__item"><span class="matrix-legend__icon matrix-legend__icon--read">□</span> 只读</span>
        <span class="matrix-legend__item"><span class="matrix-legend__icon">─</span> 无权限</span>
      </div>
    </div>

    <!-- ========== 新增/编辑用户弹窗 ========== -->
    <a-modal v-model:open="userModalOpen" :title="userModalIsEdit ? '编辑用户' : '新增用户'" :width="520" @ok="handleUserSave" @cancel="userModalOpen = false">
      <div class="user-form">
        <div class="user-form__field" v-if="!userModalIsEdit">
          <label class="user-form__label">账号 <span class="user-form__required">*</span></label>
          <a-input v-model:value="userForm.username" placeholder="请输入账号" />
        </div>
        <div class="user-form__field">
          <label class="user-form__label">姓名 <span class="user-form__required">*</span></label>
          <a-input v-model:value="userForm.name" placeholder="请输入姓名" />
        </div>
        <div class="user-form__field">
          <label class="user-form__label">邮箱</label>
          <a-input v-model:value="userForm.email" placeholder="请输入邮箱" />
        </div>
        <div class="user-form__field" v-if="!userModalIsEdit">
          <label class="user-form__label">初始密码 <span class="user-form__required">*</span></label>
          <a-input-password v-model:value="userForm.password" placeholder="请输入初始密码" />
        </div>
        <div class="user-form__field">
          <label class="user-form__label">角色 <span class="user-form__required">*</span></label>
          <a-select v-model:value="userForm.role" style="width:100%" :options="roleOptions" />
        </div>
      </div>
    </a-modal>

    <!-- ========== 角色权限编辑抽屉 ========== -->
    <a-drawer v-model:open="roleDrawerOpen" :title="`编辑权限 — ${editingRole?.label || ''}`" :width="520" @close="roleDrawerOpen = false">
      <template v-if="editingRole">
        <p class="role-drawer__desc">{{ editingRole.description }}</p>
        <div class="role-drawer__tree">
          <div v-for="mod in modules" :key="mod.key" class="role-drawer__module">
            <div class="role-drawer__module-header">
              <label class="role-drawer__check-all">
                <input type="checkbox" :checked="isModuleAllChecked(mod)" :indeterminate.prop="isModuleIndeterminate(mod)" @change="toggleModule(mod)" />
                <span class="role-drawer__module-name">{{ mod.label }}</span>
              </label>
            </div>
            <div class="role-drawer__perms">
              <label v-for="p in mod.permissions" :key="p" class="role-drawer__perm-item">
                <input type="checkbox" :checked="editingRolePerms.includes(p)" @change="togglePerm(p)" />
                <span>{{ permLabel(p) }}</span>
                <span class="role-drawer__perm-key">{{ p }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="role-drawer__footer">
          <button class="perm-btn" @click="roleDrawerOpen = false">取消</button>
          <button class="perm-btn perm-btn--primary" @click="handleSaveRolePerms" :disabled="savingRolePerms">
            {{ savingRolePerms ? '保存中...' : '保存' }}
          </button>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import {
  InputSearch as AInputSearch, Select as ASelect, Dropdown as ADropdown,
  Menu as AMenu, MenuItem as AMenuItem, Modal as AModal,
  Input as AInput, InputPassword as AInputPassword,
  Pagination as APagination, Drawer as ADrawer,
} from 'ant-design-vue'
import { authApi, type UserListItem, type RoleOut, type PermissionModule } from '../../api/auth'
import { useToast } from '../../composables/useToast'

const { success, error } = useToast()

const activeTab = ref<'users' | 'roles' | 'matrix'>('users')
const tabs = [
  { key: 'users', label: '用户管理', icon: '👥' },
  { key: 'roles', label: '角色管理', icon: '🛡' },
  { key: 'matrix', label: '权限矩阵', icon: '📊' },
]

// ── 用户管理 ──
const users = ref<UserListItem[]>([])
const usersTotal = ref(0)
const usersPage = ref(1)
const usersPageSize = ref(20)
const usersLoading = ref(false)
const userKeyword = ref('')
const userRoleFilter = ref<string | undefined>(undefined)
const userStatusFilter = ref<boolean | undefined>(undefined)

const roleOptions = computed(() => roles.value.map(r => ({ label: r.label, value: r.key })))
const roleLabelMap: Record<string, string> = { admin: '系统管理员', editor: '本体工程师', operator: '数据工程师', viewer: '只读用户' }
function roleLabel(role: string) { return roleLabelMap[role] || role }
function roleIcon(key: string) { return { admin: '🛡', editor: '🔬', operator: '📊', viewer: '👁' }[key] || '👤' }
function formatTime(ts: string | null) { return ts ? ts.replace('T', ' ').slice(0, 16) : '从未登录' }

async function fetchUsers() {
  usersLoading.value = true
  try {
    const res = await authApi.listUsers({ page: usersPage.value, page_size: usersPageSize.value, keyword: userKeyword.value || undefined, role: userRoleFilter.value, is_active: userStatusFilter.value })
    users.value = res.items
    usersTotal.value = res.total
  } catch { users.value = []; usersTotal.value = 0 } finally { usersLoading.value = false }
}

const userModalOpen = ref(false)
const userModalIsEdit = ref(false)
const editingUserId = ref<string | null>(null)
const userForm = reactive({ username: '', name: '', email: '', password: '', role: 'viewer' })

function openCreateUser() {
  userModalIsEdit.value = false; editingUserId.value = null
  Object.assign(userForm, { username: '', name: '', email: '', password: '', role: 'viewer' })
  userModalOpen.value = true
}

function openEditUser(u: UserListItem) {
  userModalIsEdit.value = true; editingUserId.value = u.id
  Object.assign(userForm, { username: u.username, name: u.name, email: u.email || '', password: '', role: u.role })
  userModalOpen.value = true
}

async function handleUserSave() {
  try {
    if (userModalIsEdit.value && editingUserId.value) {
      await authApi.updateUser(editingUserId.value, { name: userForm.name, email: userForm.email, role: userForm.role })
      success('用户已更新')
    } else {
      if (!userForm.username || !userForm.password || !userForm.name) { error('请填写必填字段'); return }
      await authApi.createUser({ username: userForm.username, password: userForm.password, name: userForm.name, email: userForm.email || undefined, role: userForm.role })
      success('用户已创建')
    }
    userModalOpen.value = false; fetchUsers()
  } catch (e: any) { error(e?.response?.data?.detail || '操作失败') }
}

async function handleUserAction(action: string, u: UserListItem) {
  if (action === 'edit') { openEditUser(u); return }
  if (action === 'toggle') {
    try { await authApi.toggleUserStatus(u.id); success(u.is_active ? '已禁用' : '已启用'); fetchUsers() } catch { error('操作失败') }
    return
  }
  if (action === 'reset') {
    const pwd = prompt(`请输入 ${u.name} 的新密码:`)
    if (!pwd) return
    try { await authApi.resetPassword(u.id, pwd); success('密码已重置') } catch { error('重置失败') }
  }
}

// ── 角色管理 ──
const roles = ref<RoleOut[]>([])
async function fetchRoles() {
  try { roles.value = await authApi.listRoles() } catch { roles.value = [] }
}

// ── 角色权限编辑抽屉 ──
const roleDrawerOpen = ref(false)
const editingRole = ref<RoleOut | null>(null)
const editingRolePerms = ref<string[]>([])
const savingRolePerms = ref(false)

function openRoleDrawer(role: RoleOut) {
  editingRole.value = role
  editingRolePerms.value = [...role.permissions]
  roleDrawerOpen.value = true
}

function togglePerm(perm: string) {
  const idx = editingRolePerms.value.indexOf(perm)
  if (idx >= 0) editingRolePerms.value.splice(idx, 1)
  else editingRolePerms.value.push(perm)
}

function isModuleAllChecked(mod: PermissionModule) {
  return mod.permissions.every(p => editingRolePerms.value.includes(p))
}

function isModuleIndeterminate(mod: PermissionModule) {
  const some = mod.permissions.some(p => editingRolePerms.value.includes(p))
  return some && !isModuleAllChecked(mod)
}

function toggleModule(mod: PermissionModule) {
  if (isModuleAllChecked(mod)) {
    mod.permissions.forEach(p => {
      const idx = editingRolePerms.value.indexOf(p)
      if (idx >= 0) editingRolePerms.value.splice(idx, 1)
    })
  } else {
    mod.permissions.forEach(p => {
      if (!editingRolePerms.value.includes(p)) editingRolePerms.value.push(p)
    })
  }
}

async function handleSaveRolePerms() {
  if (!editingRole.value) return
  savingRolePerms.value = true
  try {
    await authApi.updateRolePerms(editingRole.value.key, editingRolePerms.value)
    success('权限已保存')
    roleDrawerOpen.value = false
    fetchRoles()
  } catch (e: any) { error(e?.response?.data?.detail || '保存失败') } finally { savingRolePerms.value = false }
}

// ── 权限矩阵 ──
const modules = ref<PermissionModule[]>([])
const matrixPerms = reactive<Record<string, string[]>>({})
const matrixChanged = ref(false)
const savingMatrix = ref(false)

function getRolePerms(roleKey: string) {
  return matrixPerms[roleKey] || []
}

function isCellChanged(roleKey: string, perm: string) {
  const role = roles.value.find(r => r.key === roleKey)
  if (!role) return false
  const has = role.permissions.includes(perm)
  const nowHas = (matrixPerms[roleKey] || []).includes(perm)
  return has !== nowHas
}

function cyclePerm(roleKey: string, perm: string) {
  if (!matrixPerms[roleKey]) matrixPerms[roleKey] = [...(roles.value.find(r => r.key === roleKey)?.permissions || [])]
  const idx = matrixPerms[roleKey].indexOf(perm)
  if (idx >= 0) matrixPerms[roleKey].splice(idx, 1)
  else matrixPerms[roleKey].push(perm)
  matrixChanged.value = true
}

async function handleSaveMatrix() {
  savingMatrix.value = true
  try {
    for (const [roleKey, perms] of Object.entries(matrixPerms)) {
      await authApi.updateRolePerms(roleKey, perms)
    }
    success('权限矩阵已保存')
    matrixChanged.value = false
    fetchRoles()
  } catch (e: any) { error(e?.response?.data?.detail || '保存失败') } finally { savingMatrix.value = false }
}

async function fetchModules() {
  try {
    modules.value = await authApi.listPermissionModules()
    // 初始化矩阵权限
    roles.value.forEach(r => { matrixPerms[r.key] = [...r.permissions] })
  } catch { modules.value = [] }
}

function permLabel(perm: string) {
  const map: Record<string, string> = { 'entity:read': '读', 'entity:write': '写', 'entity:delete': '删除', 'rule:read': '读', 'rule:write': '写', 'rule:execute': '执行', 'strategy:read': '读', 'strategy:execute': '执行', 'audit:read': '读', 'admin:users': '管理' }
  return map[perm] || perm.split(':')[1]
}

function getPermSymbol(has: string[], perm: string) {
  if (!has.includes(perm)) return '─'
  if (perm.includes('delete') || perm.includes('execute') || perm.includes('admin')) return '■'
  if (perm.includes('write')) return '◧'
  return '□'
}

function getCellClass(has: string[], perm: string) {
  if (!has.includes(perm)) return 'matrix-cell--none'
  if (perm.includes('delete') || perm.includes('execute') || perm.includes('admin')) return 'matrix-cell--manage'
  if (perm.includes('write')) return 'matrix-cell--write'
  return 'matrix-cell--read'
}

onMounted(() => { fetchUsers(); fetchRoles(); fetchModules() })
</script>

<style scoped>
.perm-page { padding: 24px 32px; max-width: 1400px; }
.perm-page__title { font-size: 28px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.perm-page__subtitle { font-size: 13px; color: var(--neutral-500); margin: 6px 0 0; }
.perm-page__tabs { display: flex; gap: 4px; margin-bottom: 24px; border-bottom: 1px solid var(--neutral-100); }
.perm-tab { display: flex; align-items: center; gap: 6px; padding: 12px 20px; border: none; background: transparent; font-size: 14px; color: var(--neutral-500); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.2s; font-family: inherit; }
.perm-tab:hover { color: var(--neutral-700); background: var(--neutral-50); border-radius: 8px 8px 0 0; }
.perm-tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-600); font-weight: 600; }
.perm-tab__icon { font-size: 16px; }
.perm-section { animation: slideUp 0.3s ease; }
@keyframes slideUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.perm-section__toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 16px; }
.perm-btn { padding: 8px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); transition: all 0.2s; font-family: inherit; }
.perm-btn:hover { border-color: var(--neutral-300); }
.perm-btn--primary { background: var(--semantic-600); color: #fff; border-color: var(--semantic-600); }
.perm-btn--primary:hover { background: var(--semantic-700, #4f46e5); }
.perm-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.perm-btn--icon { background: none; border: none; cursor: pointer; font-size: 18px; color: var(--neutral-500); padding: 4px 8px; border-radius: 6px; transition: all 0.15s; }
.perm-btn--icon:hover { background: var(--neutral-100); color: var(--neutral-700); }

/* 用户表格 */
.user-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.user-table th { text-align: left; padding: 12px 14px; border-bottom: 2px solid var(--neutral-200); background: var(--neutral-50); color: var(--neutral-500); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.3px; }
.user-table td { padding: 14px; border-bottom: 1px solid var(--neutral-100); color: var(--neutral-700); }
.user-table__row { transition: background 0.15s; }
.user-table__row:hover { background: var(--neutral-50); }
.user-table__name-cell { display: flex; align-items: center; gap: 10px; }
.user-table__avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; flex-shrink: 0; }
.user-table__avatar--admin { background: #fff5f5; color: #fa5252; }
.user-table__avatar--editor { background: #edf2ff; color: #5c7cfa; }
.user-table__avatar--operator { background: #e6fcf5; color: #10b981; }
.user-table__avatar--viewer { background: var(--neutral-100); color: var(--neutral-600); }
.user-table__name { font-weight: 600; color: var(--neutral-900); }
.user-table__mono { font-family: var(--font-mono); font-size: 12px; color: var(--neutral-500); }

.role-tag { font-size: 11px; padding: 3px 10px; border-radius: 12px; font-weight: 600; }
.role--admin { background: rgba(250, 82, 82, 0.1); color: #fa5252; }
.role--editor { background: rgba(92, 124, 250, 0.1); color: #5c7cfa; }
.role--operator { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.role--viewer { background: var(--neutral-100); color: var(--neutral-600); }

.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
.status-dot--on { background: var(--status-success, #10b981); }
.status-dot--off { background: var(--neutral-300); }

.perm-pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }
.perm-pagination__total { font-size: 13px; color: var(--neutral-500); }
.perm-empty { text-align: center; padding: 60px; }
.perm-empty__icon { font-size: 48px; margin-bottom: 12px; opacity: 0.8; }
.perm-empty__title { font-size: 16px; font-weight: 600; color: var(--neutral-700); margin-bottom: 4px; }
.perm-empty__desc { font-size: 13px; color: var(--neutral-400); }

/* 角色卡片 */
.role-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.role-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: 12px; padding: 20px; transition: all 0.25s ease; cursor: pointer; }
.role-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); border-color: var(--neutral-300); }
.role-card__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.role-card__icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.role-card__icon--admin { background: #fff5f5; }
.role-card__icon--editor { background: #edf2ff; }
.role-card__icon--operator { background: #e6fcf5; }
.role-card__icon--viewer { background: var(--neutral-100); }
.role-card__system-tag { font-size: 11px; padding: 2px 8px; background: var(--neutral-100); color: var(--neutral-600); border-radius: 4px; font-weight: 500; }
.role-card__name { font-size: 16px; font-weight: 600; color: var(--neutral-900); margin-bottom: 6px; }
.role-card__desc { font-size: 13px; color: var(--neutral-500); line-height: 1.5; margin-bottom: 12px; }
.role-card__stats { display: flex; gap: 16px; font-size: 12px; color: var(--neutral-400); margin-bottom: 12px; }
.role-card__edit-btn { width: 100%; padding: 8px; border: 1px solid var(--neutral-200); background: transparent; border-radius: 8px; font-size: 13px; color: var(--neutral-600); cursor: pointer; transition: all 0.2s; font-family: inherit; }
.role-card__edit-btn:hover { border-color: var(--semantic-400); color: var(--semantic-600); background: var(--semantic-50, #f0f4ff); }

/* 角色编辑抽屉 */
.role-drawer__desc { font-size: 13px; color: var(--neutral-500); margin-bottom: 20px; }
.role-drawer__tree { display: flex; flex-direction: column; gap: 14px; }
.role-drawer__module { border: 1px solid var(--neutral-100); border-radius: 10px; overflow: hidden; }
.role-drawer__module-header { padding: 12px 16px; background: var(--neutral-50); border-bottom: 1px solid var(--neutral-100); }
.role-drawer__check-all { display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600; font-size: 14px; color: var(--neutral-800); }
.role-drawer__perms { padding: 10px 16px; display: flex; flex-direction: column; gap: 8px; }
.role-drawer__perm-item { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--neutral-700); cursor: pointer; padding: 6px 0; }
.role-drawer__perm-item input[type="checkbox"] { cursor: pointer; width: 16px; height: 16px; }
.role-drawer__perm-key { font-size: 11px; color: var(--neutral-400); font-family: var(--font-mono); margin-left: auto; }
.role-drawer__footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--neutral-100); position: sticky; bottom: 0; background: var(--neutral-0); padding-bottom: 8px; }

/* 权限矩阵 */
.matrix-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.matrix-header__hint { font-size: 13px; color: var(--neutral-400); }
.matrix-wrap { overflow-x: auto; margin-bottom: 12px; border: 1px solid var(--neutral-100); border-radius: 10px; }
.matrix-table { border-collapse: collapse; font-size: 13px; min-width: 600px; width: 100%; }
.matrix-table th { padding: 10px 12px; border-bottom: 2px solid var(--neutral-200); background: var(--neutral-50); color: var(--neutral-600); font-weight: 600; font-size: 12px; text-align: center; }
.matrix-table__corner { text-align: left !important; width: 120px; }
.matrix-table__group-th { font-size: 13px; color: var(--neutral-700); }
.matrix-table__sub-th { font-weight: 400; font-size: 11px; padding: 4px 8px; color: var(--neutral-400); }
.matrix-table__row:hover { background: var(--neutral-50); }
.matrix-table__role { font-weight: 600; color: var(--neutral-800); padding: 12px 14px; border-bottom: 1px solid var(--neutral-100); text-align: left; background: var(--neutral-0); position: sticky; left: 0; display: flex; align-items: center; gap: 8px; }
.matrix-table__role-icon { font-size: 16px; }
.matrix-table__cell { text-align: center; padding: 12px; border-bottom: 1px solid var(--neutral-100); font-size: 18px; cursor: pointer; transition: all 0.15s; }
.matrix-table__cell:hover { background: var(--neutral-100); }
.matrix-table__cell--changed { box-shadow: inset 0 0 0 2px var(--semantic-400, #818cf8); }
.matrix-cell--manage { color: var(--semantic-600, #5c7cfa); }
.matrix-cell--write { color: var(--dynamic-500, #12b886); }
.matrix-cell--read { color: var(--kinetic-500, #f59f00); }
.matrix-cell--none { color: var(--neutral-300); }

.matrix-legend { display: flex; gap: 20px; font-size: 13px; color: var(--neutral-600); }
.matrix-legend__item { display: flex; align-items: center; gap: 6px; }
.matrix-legend__icon { font-size: 16px; }
.matrix-legend__icon--manage { color: var(--semantic-600); }
.matrix-legend__icon--write { color: var(--dynamic-500); }
.matrix-legend__icon--read { color: var(--kinetic-500); }

/* 用户表单 */
.user-form { display: flex; flex-direction: column; gap: 16px; }
.user-form__field { display: flex; flex-direction: column; gap: 6px; }
.user-form__label { font-size: 13px; font-weight: 500; color: var(--neutral-700); }
.user-form__required { color: var(--status-error, #fa5252); }

@media (max-width: 1440px) { .role-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1280px) { .role-grid { grid-template-columns: 1fr; } }
</style>
