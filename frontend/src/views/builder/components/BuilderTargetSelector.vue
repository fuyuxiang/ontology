<template>
  <div class="builder-target">
    <label>{{ text('目标本体') }} <select :value="ontologyId || ''" @change="select(($event.target as HTMLSelectElement).value)"><option value="">{{ text('请选择目标本体') }}</option><option v-for="ontology in ontologies" :key="ontology.id" :value="ontology.id">{{ ontology.name }}</option></select></label>
    <form @submit.prevent="create"><input v-model="name" :placeholder="text('新本体名称')" maxlength="100" /><button :disabled="!canEdit || saving || !name.trim()">{{ text('新建本体') }}</button></form>
    <p v-if="error" role="alert">{{ error }} <button @click="load">{{ text('重试') }}</button></p>
  </div>
</template>
<script setup lang="ts">
import { useProductText } from '../../../composables/useProductText'
const { text } = useProductText()
import { useManagementPermission } from '../../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('entity:write')
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { scenarioApi, type Scenario } from '../../../api/scenarios'
const route = useRoute()
const router = useRouter()
const ontologyId = computed(() => route.query.ontology_id as string | undefined)
const ontologies = ref<Scenario[]>([])
const name = ref('')
const saving = ref(false)
const error = ref('')
async function load() { error.value = ''; try { ontologies.value = await scenarioApi.list() } catch { error.value = '本体列表加载失败' } }
async function select(id: string) { if (!id || id === ontologyId.value) return; await router.replace({ path: route.path, query: { ...route.query, ontology_id: id, code: ontologies.value.find(ontology => ontology.id === id)?.code } }) }
async function create() { if (saving.value || !name.value.trim()) return; saving.value = true; error.value = ''; try { const ontology = await scenarioApi.create({ name: name.value.trim(), code: `builder-${Date.now().toString(36)}` }); await load(); name.value = ''; await select(ontology.id) } catch (exception: any) { error.value = exception?.response?.data?.detail || '新建本体失败' } finally { saving.value = false } }
onMounted(load)
</script>
<style scoped>.builder-target { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; padding: 12px 24px; border-bottom: 1px solid #ddd; }.builder-target form { display: flex; gap: 8px; }.builder-target select,.builder-target input,.builder-target button { padding: 6px; max-width: 100%; }.builder-target p { color: #b91c1c; }</style>
