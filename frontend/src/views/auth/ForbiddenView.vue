<template>
  <a-result status="403" :title="t('common.accessDenied')" :sub-title="t('common.accessDeniedDesc')">
    <template #extra><RouterLink v-if="home !== '/forbidden'" :to="home">{{ t('shell.home') }}</RouterLink></template>
  </a-result>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../store/auth'
import { firstAccessibleRoute } from '../../utils/access'
const { t } = useI18n()
const auth = useAuthStore()
const home = computed(() => firstAccessibleRoute(permission => auth.hasPermission(permission)))
</script>
