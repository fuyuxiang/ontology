<template>
  <div class="login">
    <div class="login__card">
      <div class="login__logo">
        <img src="/images/ontology/BONC.png" alt="BONC" class="login__logo-img" />
        <div class="login__logo-text">
          <span class="login__brand">元枢</span>
          <span class="login__brand-sub">Ontology</span>
        </div>
      </div>
      <p class="login__desc">本体驱动智能策略平台</p>
      <form class="login__form" @submit.prevent="handleLogin">
        <div class="login__field">
          <label class="login__label">用户名</label>
          <input v-model="username" type="text" class="login__input" placeholder="请输入用户名" autofocus />
        </div>
        <div class="login__field">
          <label class="login__label">密码</label>
          <input v-model="password" type="password" class="login__input" placeholder="请输入密码" />
        </div>
        <p v-if="error" class="login__error">{{ error }}</p>
        <button type="submit" class="login__btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('admin')
const password = ref('bonc')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login({ username: username.value, password: password.value })
    router.push('/dashboard')
  } catch (e: any) {
    error.value = e?.message || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--sidebar-bg);
}
.login__card {
  width: 380px;
  padding: 48px 40px;
  background: var(--neutral-950);
  border-radius: 16px;
  border: 1px solid var(--neutral-800);
}
.login__logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.login__logo-img {
  width: 40px;
  height: 40px;
  border-radius: 8px;
}
.login__logo-text {
  display: flex;
  flex-direction: column;
}
.login__brand {
  font-size: var(--text-h2-size);
  font-weight: 700;
  color: var(--neutral-0);
  line-height: 1.2;
}
.login__brand-sub {
  font-size: var(--text-code-size);
  color: var(--neutral-600);
  font-weight: 500;
}
.login__desc {
  font-size: var(--text-body-size);
  color: var(--neutral-600);
  margin-bottom: 32px;
}
.login__form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.login__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.login__label {
  font-size: var(--text-code-size);
  font-weight: 500;
  color: var(--neutral-500);
}
.login__input {
  height: 40px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--neutral-800);
  background: var(--neutral-950);
  color: var(--neutral-0);
  font-size: var(--text-body-size);
  outline: none;
  transition: border-color 0.15s;
}
.login__input:focus {
  border-color: var(--semantic-600);
}
.login__input::placeholder {
  color: var(--neutral-700);
}
.login__error {
  font-size: var(--text-code-size);
  color: var(--status-error);
  margin: -8px 0 0;
}
.login__btn {
  height: 42px;
  border-radius: 8px;
  border: none;
  background: var(--semantic-600);
  color: var(--neutral-0);
  font-size: var(--text-body-size);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 4px;
}
.login__btn:hover:not(:disabled) {
  background: var(--semantic-600);
}
.login__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
