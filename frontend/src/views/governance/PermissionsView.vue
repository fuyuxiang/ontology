<template>
  <div class="dashboard-container">
    <!-- Header -->
    <div class="dashboard-header">
      <h2>权限管理</h2>
      <div class="header-right">
        <a-segmented v-model:value="activeTab" :options="tabOptions" />
      </div>
    </div>

    <!-- ========== 用户管理 ========== -->
    <a-card v-if="activeTab === 'users'" :bordered="false" style="margin-top: 16px;">
      <div class="section-toolbar">
        <a-input-search v-model:value="userKeyword" placeholder="搜索姓名或账号" style="width: 260px" allow-clear @search="fetchUsers" @change="(e: Event) => { if (!(e.target as HTMLInputElement).value) fetchUsers() }" />
        <a-select v-model:value="userRoleFilter" placeholder="全部角色" allow-clear style="width: 140px" :options="roleOptions" @change="fetchUsers" />
        <a-select v-model:value="userStatusValue" placeholder="全部状态" allow-clear style="width: 120px" :options="userStatusOptions" @change="fetchUsers" />
        <a-button type="primary" style="margin-left:auto" @click="openCreateUser">＋ 新增用户</a-button>
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
                <a-button type="text" size="small">⋯</a-button>
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
      <div v-else-if="!usersLoading" class="empty-state">
        <div class="empty-state__icon">👥</div>
        <p class="empty-state__title">暂无用户</p>
        <p class="empty-state__desc">点击「新增用户」添加第一个用户</p>
      </div>

      <div class="section-pagination" v-if="usersTotal > 0">
        <span class="section-pagination__total">共 {{ usersTotal }} 人</span>
        <a-pagination v-model:current="usersPage" :page-size="usersPageSize" :total="usersTotal" size="small" @change="fetchUsers" />
      </div>
    </a-card>

    <!-- ========== 角色管理 ========== -->
    <a-card v-if="activeTab === 'roles'" :bordered="false" style="margin-top: 16px;">
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
          <a-button block size="small" @click.stop="openRoleDrawer(role)">编辑权限</a-button>
        </div>
      </div>
    </a-card>

    <!-- ========== 权限矩阵 ========== -->
    <a-card v-if="activeTab === 'matrix'" :bordered="false" style="margin-top: 16px;">
      <div class="matrix-header">
        <span class="matrix-header__hint">点击单元格可切换权限级别</span>
        <a-button v-if="matrixChanged" type="primary" @click="handleSaveMatrix" :loading="savingMatrix">保存变更</a-button>
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
    </a-card>

    <!-- ========== 新增/编辑用户弹窗 ========== -->
    <a-modal v-model:open="userModalOpen" :title="userModalIsEdit ? '编辑用户' : '新增用户'" :width="520" @ok="handleUserSave" @cancel="userModalOpen = false">
      <div class="modal-form">
        <div class="modal-form__field" v-if="!userModalIsEdit">
          <label class="modal-form__label">账号 <span class="modal-form__required">*</span></label>
          <a-input v-model:value="userForm.username" placeholder="请输入账号" />
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">姓名 <span class="modal-form__required">*</span></label>
          <a-input v-model:value="userForm.name" placeholder="请输入姓名" />
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">邮箱</label>
          <a-input v-model:value="userForm.email" placeholder="请输入邮箱" />
        </div>
        <div class="modal-form__field" v-if="!userModalIsEdit">
          <label class="modal-form__label">初始密码 <span class="modal-form__required">*</span></label>
          <a-input-password v-model:value="userForm.password" placeholder="请输入初始密码" />
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">角色 <span class="modal-form__required">*</span></label>
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
          <a-button @click="roleDrawerOpen = false">取消</a-button>
          <a-button type="primary" @click="handleSaveRolePerms" :loading="savingRolePerms">保存</a-button>
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
  Pagination as APagination, Drawer as ADrawer, Card as ACard,
  Button as AButton, Segmented as ASegmented,
} from 'ant-design-vue'
import { authApi, type UserListItem, type RoleOut, type PermissionModule } from '../../api/auth'
import { useToast } from '../../composables/useToast'

const { success, error } = useToast()

const activeTab = ref<'users' | 'roles' | 'matrix'>('users')
const tabOptions = [
  { label: '👥 用户管理', value: 'users' },
  { label: '🛡 角色管理', value: 'roles' },
  { label: '📊 权限矩阵', value: 'matrix' },
]

const users = ref<UserListItem[]>([])
const usersTotal = ref(0)
const usersPage = ref(1)
const usersPageSize = ref(20)
const usersLoading = ref(false)
const userKeyword = ref('')
const userRoleFilter = ref<string | undefined>(undefined)
const userStatusFilter = ref<boolean | undefined>(undefined)
// a-select 的 SelectValue 类型不含 boolean，但运行时支持布尔 value；此处用字符串选项承载，change 时再转布尔
const userStatusOptions = [{ label: '启用', value: 'true' }, { label: '禁用', value: 'false' }]
const userStatusValue = computed<string | undefined>({
  get: () => userStatusFilter.value === undefined ? undefined : String(userStatusFilter.value),
  set: (v) => { userStatusFilter.value = v === undefined ? undefined : v === 'true' },
})

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

const roles = ref<RoleOut[]>([])
async function fetchRoles() {
  try { roles.value = await authApi.listRoles() } catch { roles.value = [] }
}

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

const modules = ref<PermissionModule[]>([])
const matrixPerms = reactive<Record<string, string[]>>({})
const matrixChanged = ref(false)
const savingMatrix = ref(false)

function getRolePerms(roleKey: string) { return matrixPerms[roleKey] || [] }

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
.dashboard-container { padding: 24px 32px; }
.dashboard-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.dashboard-header h2 { margin: 0; font-size: 22px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }

.section-toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 16px; }
.section-pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }
.section-pagination__total { font-size: 13px; color: var(--color-text-secondary, #888); }

.empty-state { text-align: center; padding: 60px; }
.empty-state__icon { font-size: 48px; margin-bottom: 12px; opacity: 0.8; }
.empty-state__title { font-size: 16px; font-weight: 600; color: var(--color-text-primary, #333); margin-bottom: 4px; }
.empty-state__desc { font-size: 13px; color: var(--color-text-secondary, #888); }

.user-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.user-table th { text-align: left; padding: 12px 14px; border-bottom: 2px solid var(--color-bg-elevated, #f0f0f0); background: var(--color-bg-container, #fafafa); color: var(--color-text-secondary, #888); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.3px; }
.user-table td { padding: 14px; border-bottom: 1px solid var(--color-bg-container, #fafafa); color: var(--color-text-primary, #333); }
.user-table__row { transition: background 0.15s; }
.user-table__row:hover { background: var(--color-bg-container, #fafafa); }
.user-table__name-cell { display: flex; align-items: center; gap: 10px; }
.user-table__avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; flex-shrink: 0; }
.user-table__avatar--admin { background: #fff5f5; color: #fa5252; }
.user-table__avatar--editor { background: #edf2ff; color: #5c7cfa; }
.user-table__avatar--operator { background: #e6fcf5; color: #10b981; }
.user-table__avatar--viewer { background: var(--color-bg-container, #fafafa); color: var(--color-text-secondary, #888); }
.user-table__name { font-weight: 600; }
.user-table__mono { font-family: var(--font-mono, monospace); font-size: 12px; color: var(--color-text-secondary, #888); }

.role-tag { font-size: 11px; padding: 3px 10px; border-radius: 12px; font-weight: 600; }
.role--admin { background: rgba(250, 82, 82, 0.1); color: #fa5252; }
.role--editor { background: rgba(92, 124, 250, 0.1); color: #5c7cfa; }
.role--operator { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.role--viewer { background: var(--color-bg-container, #fafafa); color: var(--color-text-secondary, #888); }

.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
.status-dot--on { background: #10b981; }
.status-dot--off { background: var(--color-bg-elevated, #d0d0d0); }

.role-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.role-card { background: var(--color-bg-container, #fafafa); border: 1px solid var(--color-bg-elevated, #f0f0f0); border-radius: 8px; padding: 20px; transition: all 0.25s ease; cursor: pointer; }
.role-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.role-card__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.role-card__icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.role-card__icon--admin { background: #fff5f5; }
.role-card__icon--editor { background: #edf2ff; }
.role-card__icon--operator { background: #e6fcf5; }
.role-card__icon--viewer { background: var(--color-bg-elevated, #f0f0f0); }
.role-card__system-tag { font-size: 11px; padding: 2px 8px; background: var(--color-bg-elevated, #f0f0f0); color: var(--color-text-secondary, #888); border-radius: 4px; }
.role-card__name { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.role-card__desc { font-size: 13px; color: var(--color-text-secondary, #888); line-height: 1.5; margin-bottom: 12px; }
.role-card__stats { display: flex; gap: 16px; font-size: 12px; color: var(--color-text-secondary, #888); margin-bottom: 12px; }

.matrix-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.matrix-header__hint { font-size: 13px; color: var(--color-text-secondary, #888); }
.matrix-wrap { overflow-x: auto; margin-bottom: 12px; border: 1px solid var(--color-bg-elevated, #f0f0f0); border-radius: 8px; }
.matrix-table { border-collapse: collapse; font-size: 13px; min-width: 600px; width: 100%; }
.matrix-table th { padding: 10px 12px; border-bottom: 2px solid var(--color-bg-elevated, #f0f0f0); background: var(--color-bg-container, #fafafa); color: var(--color-text-secondary, #888); font-weight: 600; font-size: 12px; text-align: center; }
.matrix-table__corner { text-align: left !important; width: 120px; }
.matrix-table__group-th { font-size: 13px; color: var(--color-text-primary, #333); }
.matrix-table__sub-th { font-weight: 400; font-size: 11px; padding: 4px 8px; color: var(--color-text-secondary, #888); }
.matrix-table__row:hover { background: var(--color-bg-container, #fafafa); }
.matrix-table__role { font-weight: 600; padding: 12px 14px; border-bottom: 1px solid var(--color-bg-container, #fafafa); text-align: left; display: flex; align-items: center; gap: 8px; }
.matrix-table__role-icon { font-size: 16px; }
.matrix-table__cell { text-align: center; padding: 12px; border-bottom: 1px solid var(--color-bg-container, #fafafa); font-size: 18px; cursor: pointer; transition: all 0.15s; }
.matrix-table__cell:hover { background: var(--color-bg-elevated, #f0f0f0); }
.matrix-table__cell--changed { box-shadow: inset 0 0 0 2px #818cf8; }
.matrix-cell--manage { color: #5c7cfa; }
.matrix-cell--write { color: #12b886; }
.matrix-cell--read { color: #f59f00; }
.matrix-cell--none { color: #ccc; }
.matrix-legend { display: flex; gap: 20px; font-size: 13px; color: var(--color-text-secondary, #888); }
.matrix-legend__item { display: flex; align-items: center; gap: 6px; }
.matrix-legend__icon { font-size: 16px; }
.matrix-legend__icon--manage { color: #5c7cfa; }
.matrix-legend__icon--write { color: #12b886; }
.matrix-legend__icon--read { color: #f59f00; }

.role-drawer__desc { font-size: 13px; color: var(--color-text-secondary, #888); margin-bottom: 20px; }
.role-drawer__tree { display: flex; flex-direction: column; gap: 14px; }
.role-drawer__module { border: 1px solid var(--color-bg-elevated, #f0f0f0); border-radius: 8px; overflow: hidden; }
.role-drawer__module-header { padding: 12px 16px; background: var(--color-bg-container, #fafafa); border-bottom: 1px solid var(--color-bg-elevated, #f0f0f0); }
.role-drawer__check-all { display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600; font-size: 14px; }
.role-drawer__perms { padding: 10px 16px; display: flex; flex-direction: column; gap: 8px; }
.role-drawer__perm-item { display: flex; align-items: center; gap: 10px; font-size: 13px; cursor: pointer; padding: 6px 0; }
.role-drawer__perm-item input[type="checkbox"] { cursor: pointer; width: 16px; height: 16px; }
.role-drawer__perm-key { font-size: 11px; color: var(--color-text-secondary, #888); font-family: var(--font-mono, monospace); margin-left: auto; }
.role-drawer__footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--color-bg-elevated, #f0f0f0); }

.modal-form { display: flex; flex-direction: column; gap: 16px; }
.modal-form__field { display: flex; flex-direction: column; gap: 6px; }
.modal-form__label { font-size: 13px; font-weight: 500; }
.modal-form__required { color: #fa5252; }

@media (max-width: 1440px) { .role-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1280px) { .role-grid { grid-template-columns: 1fr; } }
</style>
