<template>
  <div class="perm-page">
    <div class="perm-page__header">
      <h1 class="text-display">权限管理</h1>
      <p class="text-caption" style="margin-top: 4px;">用户账号 · 角色配置 · 权限矩阵</p>
    </div>

    <div class="perm-page__tabs">
      <button v-for="tab in tabs" :key="tab.key" class="perm-tab" :class="{ 'perm-tab--active': activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
    </div>

    <!-- ========== 用户管理 ========== -->
    <div v-if="activeTab === 'users'" class="perm-section">
      <div class="perm-section__toolbar">
        <a-input-search v-model:value="userKeyword" placeholder="搜索姓名或账号" style="width: 260px" allow-clear @search="fetchUsers" @change="(e: Event) => { if (!(e.target as HTMLInputElement).value) fetchUsers() }" />
        <a-select v-model:value="userRoleFilter" placeholder="全部角色" allow-clear style="width: 140px" :options="roleOptions" @change="fetchUsers" />
        <a-select v-model:value="userStatusFilter" placeholder="全部状态" allow-clear style="width: 120px" :options="[{label:'启用',value:true},{label:'禁用',value:false}]" @change="fetchUsers" />
        <button class="perm-btn perm-btn--primary" style="margin-left:auto" @click="openCreateUser">＋ 新增用户</button>
      </div>

      <table class="data-table" v-if="users.length">
        <thead><tr><th style="width:100px">姓名</th><th style="width:130px">账号</th><th style="width:160px">邮箱</th><th style="width:120px">角色</th><th style="width:80px">状态</th><th style="width:140px">最近登录</th><th style="width:80px">操作</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="perm-table__name">{{ u.name }}</td>
            <td class="perm-table__mono">{{ u.username }}</td>
            <td class="perm-table__mono">{{ u.email || '-' }}</td>
            <td><span class="role-tag" :class="`role--${u.role}`">{{ roleLabel(u.role) }}</span></td>
            <td><span :class="u.is_active ? 'status--on' : 'status--off'">● {{ u.is_active ? '启用' : '禁用' }}</span></td>
            <td class="perm-table__mono">{{ formatTime(u.last_login_at) }}</td>
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
        <div style="font-size:36px;margin-bottom:8px">👥</div>
        <p>暂无用户</p>
        <p class="text-caption">点击「新增用户」添加第一个用户</p>
      </div>

      <div class="perm-pagination" v-if="usersTotal > 0">
        <span class="perm-pagination__total">共 {{ usersTotal }} 人</span>
        <a-pagination v-model:current="usersPage" :page-size="usersPageSize" :total="usersTotal" size="small" @change="fetchUsers" />
      </div>
    </div>

    <!-- ========== 角色管理 ========== -->
    <div v-if="activeTab === 'roles'" class="perm-section">
      <div class="role-grid">
        <div v-for="role in roles" :key="role.key" class="role-card">
          <div class="role-card__icon" :class="`role-card__icon--${role.key}`">{{ roleIcon(role.key) }}</div>
          <div class="role-card__name">{{ role.label }}</div>
          <span v-if="role.is_system" class="role-card__system-tag">系统</span>
          <div class="role-card__desc">{{ role.description }}</div>
          <div class="role-card__stats">👤 {{ role.user_count }}人 · 🔑 {{ role.permissions.length }}项权限</div>
          <button class="role-card__edit-btn" @click="openRoleDrawer(role)">编辑权限</button>
        </div>
      </div>
    </div>

    <!-- ========== 权限矩阵 ========== -->
    <div v-if="activeTab === 'matrix'" class="perm-section">
      <div class="matrix-wrap">
        <table class="matrix-table">
          <thead>
            <tr>
              <th class="matrix-table__corner">角色</th>
              <th v-for="mod in modules" :key="mod.key" :colspan="mod.permissions.length">{{ mod.label }}</th>
            </tr>
            <tr>
              <th></th>
              <template v-for="mod in modules" :key="mod.key">
                <th v-for="p in mod.permissions" :key="p" class="matrix-table__sub-th">{{ permLabel(p) }}</th>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr v-for="role in roles" :key="role.key">
              <td class="matrix-table__role">{{ role.label }}</td>
              <template v-for="mod in modules" :key="mod.key">
                <td v-for="p in mod.permissions" :key="p" class="matrix-table__cell" :class="getCellClass(role.permissions, p)">
                  {{ getPermSymbol(role.permissions, p) }}
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
  { key: 'users', label: '用户管理' },
  { key: 'roles', label: '角色管理' },
  { key: 'matrix', label: '权限矩阵' },
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
    // 取消全部
    mod.permissions.forEach(p => {
      const idx = editingRolePerms.value.indexOf(p)
      if (idx >= 0) editingRolePerms.value.splice(idx, 1)
    })
  } else {
    // 全选
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
    fetchModules() // 刷新矩阵
  } catch (e: any) { error(e?.response?.data?.detail || '保存失败') } finally { savingRolePerms.value = false }
}

// ── 权限矩阵 ──
const modules = ref<PermissionModule[]>([])
async function fetchModules() {
  try { modules.value = await authApi.listPermissionModules() } catch { modules.value = [] }
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
.perm-page__header { margin-bottom: 16px; }
.perm-page__tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--neutral-100); }
.perm-tab { padding: 10px 18px; border: none; background: transparent; font-size: 13px; color: var(--neutral-500); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; font-family: inherit; }
.perm-tab:hover { color: var(--neutral-800); }
.perm-tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-600); font-weight: 500; }
.perm-section { animation: fadeIn 0.2s; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

.perm-section__toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; }
.perm-btn { padding: 6px 16px; border-radius: 6px; font-size: 13px; cursor: pointer; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); transition: all 0.15s; font-family: inherit; }
.perm-btn--primary { background: var(--semantic-600); color: #fff; border-color: var(--semantic-600); }
.perm-btn--primary:hover { opacity: 0.9; }
.perm-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.perm-btn--icon { background: none; border: none; cursor: pointer; font-size: 16px; color: var(--neutral-500); padding: 4px 8px; border-radius: 4px; }
.perm-btn--icon:hover { background: var(--neutral-100); }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--neutral-200); background: var(--neutral-50); color: var(--neutral-500); font-weight: 600; font-size: 12px; }
.data-table td { padding: 12px; border-bottom: 1px solid var(--neutral-100); color: var(--neutral-700); }
.perm-table__name { font-weight: 600; color: var(--neutral-900); }
.perm-table__mono { font-family: var(--font-mono); font-size: 12px; color: var(--neutral-600); }

.role-tag { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.role--admin { background: #fff5f5; color: #fa5252; }
.role--editor { background: #edf2ff; color: #5c7cfa; }
.role--operator { background: #e6fcf5; color: #10b981; }
.role--viewer { background: var(--neutral-100); color: var(--neutral-600); }

.status--on { color: var(--status-success, #10b981); font-size: 12px; }
.status--off { color: var(--neutral-400); font-size: 12px; }

.perm-pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }
.perm-pagination__total { font-size: 13px; color: var(--neutral-500); }
.perm-empty { text-align: center; padding: 60px; color: var(--neutral-400); }

/* 角色卡片 */
.role-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.role-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: 12px; padding: 20px; transition: all 0.2s; position: relative; }
.role-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,0.08)); }
.role-card__icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; margin-bottom: 12px; }
.role-card__icon--admin { background: #fff5f5; }
.role-card__icon--editor { background: #edf2ff; }
.role-card__icon--operator { background: #e6fcf5; }
.role-card__icon--viewer { background: var(--neutral-100); }
.role-card__name { font-size: 16px; font-weight: 600; color: var(--neutral-900); }
.role-card__system-tag { position: absolute; top: 16px; right: 16px; font-size: 11px; padding: 2px 8px; background: var(--neutral-100); color: var(--neutral-600); border-radius: 4px; }
.role-card__desc { font-size: 13px; color: var(--neutral-500); margin-top: 8px; line-height: 1.5; }
.role-card__stats { font-size: 12px; color: var(--neutral-400); margin-top: 12px; }
.role-card__edit-btn { margin-top: 12px; width: 100%; padding: 6px; border: 1px solid var(--neutral-200); background: transparent; border-radius: 6px; font-size: 12px; color: var(--neutral-600); cursor: pointer; transition: all 0.15s; font-family: inherit; }
.role-card__edit-btn:hover { border-color: var(--semantic-400); color: var(--semantic-600); }

/* 角色编辑抽屉 */
.role-drawer__desc { font-size: 13px; color: var(--neutral-500); margin-bottom: 20px; }
.role-drawer__tree { display: flex; flex-direction: column; gap: 16px; }
.role-drawer__module { border: 1px solid var(--neutral-100); border-radius: 8px; overflow: hidden; }
.role-drawer__module-header { padding: 10px 14px; background: var(--neutral-50); border-bottom: 1px solid var(--neutral-100); }
.role-drawer__check-all { display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 500; font-size: 14px; color: var(--neutral-800); }
.role-drawer__module-name { }
.role-drawer__perms { padding: 8px 14px; display: flex; flex-direction: column; gap: 6px; }
.role-drawer__perm-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--neutral-700); cursor: pointer; padding: 4px 0; }
.role-drawer__perm-item input[type="checkbox"] { cursor: pointer; }
.role-drawer__perm-item input[type="checkbox"]:disabled { cursor: not-allowed; opacity: 0.5; }
.role-drawer__perm-key { font-size: 11px; color: var(--neutral-400); font-family: var(--font-mono); margin-left: auto; }
.role-drawer__system-notice { margin-top: 20px; padding: 10px 14px; background: #fff9db; border-radius: 6px; font-size: 13px; color: #e67700; }
.role-drawer__footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--neutral-100); position: sticky; bottom: 0; background: var(--neutral-0); padding-bottom: 8px; }

/* 权限矩阵 */
.matrix-wrap { overflow-x: auto; margin-bottom: 12px; }
.matrix-table { border-collapse: collapse; font-size: 13px; min-width: 600px; }
.matrix-table th { padding: 8px 12px; border-bottom: 1px solid var(--neutral-200); background: var(--neutral-50); color: var(--neutral-600); font-weight: 600; font-size: 12px; text-align: center; }
.matrix-table__corner { text-align: left !important; width: 120px; }
.matrix-table__sub-th { font-weight: 400; font-size: 11px; padding: 4px 8px; color: var(--neutral-400); }
.matrix-table__role { font-weight: 500; color: var(--neutral-800); padding: 10px 12px; border-bottom: 1px solid var(--neutral-100); text-align: left; background: var(--neutral-0); position: sticky; left: 0; }
.matrix-table__cell { text-align: center; padding: 10px; border-bottom: 1px solid var(--neutral-100); font-size: 16px; }
.matrix-cell--manage { color: var(--semantic-600, #5c7cfa); }
.matrix-cell--write { color: var(--dynamic-500, #12b886); }
.matrix-cell--read { color: var(--kinetic-500, #f59f00); }
.matrix-cell--none { color: var(--neutral-300); }

.matrix-legend { display: flex; gap: 20px; font-size: 13px; color: var(--neutral-600); }
.matrix-legend__item { display: flex; align-items: center; gap: 6px; }
.matrix-legend__icon { font-size: 14px; }
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
