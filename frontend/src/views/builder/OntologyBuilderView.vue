<template>
  <div class="builder-page">
    <BuilderTargetSelector />
    <div v-if="targetOntologyId" class="builder-page__toolbar">
      <span class="builder-page__toolbar-label">{{ text('工具选择') }}</span>
      <select class="builder-page__select" v-model="editorMode">
        <option value="local">{{ text('本地构建') }}</option>
        <option value="protege">Protégé</option>
        <option value="webowl">WebOWL</option>
        <option value="vocbench">VocBench</option>
      </select><button v-if="editorMode !== 'local'" :disabled="bridging" @click="bridgeEditor">{{ text(bridging ? '解析中…' : '进入业务审核、映射与发布') }}</button>
    </div>

    <template v-if="targetOntologyId && editorMode === 'local'">
      <BuilderShell
        v-if="session"
        :key="session.sessionId"
        :session="session"
        @goto-studio="gotoStudio"
      />
      <div v-else class="builder-page__loading">正在初始化构建会话…</div>
    </template>

    <ProtegeEditor v-else-if="targetOntologyId && editorMode === 'protege'" />
    <WebVowlEditor v-else-if="targetOntologyId && editorMode === 'webowl'" />
    <VocBenchEditor v-else-if="targetOntologyId" />
  </div>
</template>

<script setup lang="ts">
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../../store/auth'
import { matchesBuilderSession } from '../../utils/builderSession'
import BuilderTargetSelector from './components/BuilderTargetSelector.vue'
import { useBuilderStore } from '../../store/builder'
import ProtegeEditor from './components/protege/ProtegeEditor.vue'
import WebVowlEditor from './components/WebVowlEditor.vue'
import VocBenchEditor from './components/VocBenchEditor.vue'
import { useOwlEditorStore } from '../../store/owlEditor'
import { entityApi } from '../../api/ontology'
import { message } from 'ant-design-vue'
import type { OntologyObjectDraft, OntologyRelationDraft } from '../../types/builder'
import BuilderShell from './components/BuilderShell.vue'

const router = useRouter()
const route = useRoute()
const store = useBuilderStore()
const auth = useAuthStore()
const owl = useOwlEditorStore()
const bridging = ref(false)
let bridgeRequest = 0
let mounted = true
onBeforeUnmount(() => { mounted = false; ++bridgeRequest })
const targetOntologyId = computed(() => (route.query.ontology_id as string) || undefined)
const { sessions, activeSession } = storeToRefs(store)

const editorMode = ref<'local' | 'protege' | 'webowl' | 'vocbench'>('local')

const session = computed(() => {
  const matches = (draft: import('../../types/builder').BuilderSession) =>
    matchesBuilderSession(draft, 'manual', targetOntologyId.value, auth.user?.id)
  if (activeSession.value && matches(activeSession.value)) return activeSession.value
  return sessions.value.find(draft => matches(draft) && draft.status !== 'published') || null
})

function ensureSession() {
  if (editorMode.value === 'local' && !session.value) {
    store.createSession({
      ontologyName: `本地构建-${Date.now().toString(36).slice(-4)}`,
      buildMethod: 'manual', ontologyId: targetOntologyId.value, builderKind: 'manual',
    })
  }
}

watch([targetOntologyId, () => auth.user?.id], ([ontologyId, ownerId]) => { owl.setScope(ontologyId && ownerId ? `${ownerId}:${ontologyId}` : null) }, { immediate: true })
async function bridgeEditor() {
  if (bridging.value || !targetOntologyId.value) return
  bridging.value = true
  const request = ++bridgeRequest, ontologyId = targetOntologyId.value, ownerId = auth.user?.id
  try {
    owl.saveDraft()
    const preview = await entityApi.previewFile(new File([owl.exportOwlXml()], 'ontology.owl', { type:'application/xml' }), 'owl')
    if (!mounted || request !== bridgeRequest || ontologyId !== targetOntologyId.value || ownerId !== auth.user?.id) return
    if (!preview.objects.length) throw new Error('编辑器没有可导入对象；请先定义类及其数据属性')
    ensureSession()
    if (!session.value) store.createSession({ ontologyName:'OWL构建', buildMethod:'manual', ontologyId:targetOntologyId.value, builderKind:'manual' })
    const stamp = Date.now().toString(36), names = new Map<string,string>()
    const objects: OntologyObjectDraft[] = preview.objects.map((object, index) => { const id = `obj-${stamp}-${index}`; names.set(object.name,id); return { id, name:object.name, displayName:object.display_name || object.name, tier:(object.tier || 2) as 1|2|3, namespace:object.namespace || undefined, description:object.description || '', primaryKey:object.primary_key || 'id', icon:'🔷', instanceCount:0, backing_asset_ids:[], properties:object.properties.map((property, field) => ({ id:`p-${stamp}-${index}-${field}`, name:property.name, displayName:property.display_name || property.name, type:property.type || 'string', required:property.required, description:property.description, source_column:property.source_field, source_field:property.source_field, source_table:property.source_table })), derivedProperties:[], actions:[], approved:false } })
    const relations: OntologyRelationDraft[] = preview.relations.map((relation,index) => ({ id:`r-${stamp}-${index}`, name:relation.name, displayName:relation.display_name || relation.name, source:names.get(relation.source)!, target:names.get(relation.target)!, cardinality:relation.cardinality === '1:1' || relation.cardinality === 'N:1' || relation.cardinality === 'N:N' ? relation.cardinality : '1:N', sourceField:relation.source_field, targetField:relation.target_field, description:relation.description, relationType:'ObjectProperty', semanticType:'association' }))
    store.patchActive({ ontologyObjects:objects, ontologyRelations:relations, status:'pending_review' })
    editorMode.value = 'local'
    message.success('定义已导入当前本体草稿，请审核并绑定真实业务数据')
    if (preview.warnings?.length) message.warning({content:preview.warnings.join('；'),duration:10})
  } catch (exception:any) { if (mounted && request === bridgeRequest && ontologyId === targetOntologyId.value && ownerId === auth.user?.id) message.error(exception?.response?.data?.detail || exception.message || '导入编辑器定义失败') }
  finally { if (request === bridgeRequest) bridging.value = false }
}

watch([targetOntologyId, () => auth.user?.id], () => { ++bridgeRequest; bridging.value = false })

function gotoStudio() {
  if (route.query.from === 'ontology-detail' && route.query.code) {
    router.push(`/ontology/list/${route.query.code}`)
  } else {
    router.push('/ontology/list')
  }
}

watch(editorMode, (mode) => {
  if (mode === 'local') ensureSession()
})

onMounted(() => {
  if (editorMode.value === 'local') {
    if (session.value) {
      store.setActiveSession(session.value.sessionId)
    } else {
      ensureSession()
    }
  }
})
watch(targetOntologyId, () => {
  if (!targetOntologyId.value) return
  if (!session.value) store.createSession({ ontologyName: 'manual构建', buildMethod: 'manual', ontologyId: targetOntologyId.value, builderKind: 'manual' })
  else store.setActiveSession(session.value.sessionId)

})
</script>

<style scoped>
.builder-page { height: 100%; display: flex; flex-direction: column; }
.builder-page__toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: #f5f5f5;
  border-bottom: 1px solid #d8d8d8;
  flex-shrink: 0;
}
.builder-page__toolbar-label {
  font-size: 12px;
  color: #555;
}
.builder-page__select {
  font-size: 12px;
  padding: 3px 8px;
  border: 1px solid #c0c0c0;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
}
.builder-page__loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}
</style>
