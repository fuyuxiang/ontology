import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { createPinia, setActivePinia } from 'pinia'
import { reactive, createRenderer, nextTick, ref, h } from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'
import { ontology as roundtripOntology } from './owl-roundtrip-fixture.mjs'

function compile(source) {
  source = source.replace(/import \{ authenticatedFetch \} from[^\n]+/g, 'const authenticatedFetch = (...args) => globalThis.fetch(...args)')
    .replace(/import \{ useProductText \} from[^\n]+/g, 'const useProductText = () => ({text: value => value})')
    .replace(/import \{ captureAuthSession, refreshAccessToken \} from[^\n]+/g, "const captureAuthSession = () => ({id: globalThis.builderTestAuth.token}), refreshAccessToken = async () => globalThis.builderTestAuth.token")
  return ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText }
function moduleUrl(source) { return `data:text/javascript;base64,${Buffer.from(compile(source)).toString('base64')}` }
const decoderUrl = moduleUrl(readFileSync(new URL('../src/components/logic/sseDecoder.ts', import.meta.url), 'utf8'))
const sseSource = readFileSync(new URL('../src/api/sse.ts', import.meta.url), 'utf8').replace("'../components/logic/sseDecoder'", JSON.stringify(decoderUrl)).replace("import { authHeaders } from '../utils/authHeaders'", 'const authHeaders = () => ({})')
const { readJsonSse } = await import(moduleUrl(sseSource))
const signatureUrl = moduleUrl(readFileSync(new URL('../src/utils/builderSession.ts', import.meta.url), 'utf8'))
const { builderContentSignature, matchesBuilderSession } = await import(signatureUrl)
const memory = new Map()
globalThis.localStorage = { getItem: key => memory.get(key) || null, setItem: (key, value) => memory.set(key, value), removeItem: key => memory.delete(key) }
globalThis.builderTestAuth = reactive({ user: { id: 'account-a' } })
const storeSource = readFileSync(new URL('../src/store/builder.ts', import.meta.url), 'utf8').replace("'pinia'", JSON.stringify(import.meta.resolve('pinia'))).replace("'vue'", JSON.stringify(import.meta.resolve('vue'))).replace("import { useAuthStore } from './auth'", 'const useAuthStore = () => globalThis.builderTestAuth').replace("'../utils/builderSession'", JSON.stringify(signatureUrl))
const { useBuilderStore } = await import(moduleUrl(storeSource))
const iriUrl = moduleUrl(readFileSync(new URL('../src/utils/owl/iri.ts', import.meta.url), 'utf8'))
const serializerSource = readFileSync(new URL('../src/utils/owl/serializer.ts', import.meta.url), 'utf8').replace("'./iri'", JSON.stringify(iriUrl))
const { serializeToOwlXml } = await import(moduleUrl(serializerSource))

test('OWL editor exports the exact common artifact consumed by the backend importer', () => {
  const fixture = readFileSync(new URL('../../backend/tests/fixtures/builder-owl-roundtrip.owl',import.meta.url),'utf8')
  assert.equal(serializeToOwlXml(roundtripOntology),fixture)
  assert.match(fixture, /<Prefix name="ex:"/)
  assert.match(fixture, /设备 &amp; 告警/)
})

function stream(text, size = 1) {
  const bytes = new TextEncoder().encode(text)
  return new Response(new ReadableStream({ start(controller) { for (let i = 0; i < bytes.length; i += size) controller.enqueue(bytes.slice(i, i + size)); controller.close() } }), { status: 200 })
}

test('builder streams preserve byte-split UTF-8 and require terminal plus result', async () => {
  const events = []
  await readJsonSse(stream('data: {"event":"result","data":{"name":"设备🙂"}}\r\n\r\ndata: [DONE]'), event => events.push(event), true)
  assert.equal(events[0].data.name, '设备🙂')
  await assert.rejects(readJsonSse(stream('data: [DONE]\n\n'), () => {}, true), /未返回有效结果/)
  await assert.rejects(readJsonSse(stream('data: {"event":"result"}\n\n'), () => {}, true), /提前结束/)
  await assert.rejects(readJsonSse(stream('data: {"event":"error","message":"源连接失败"}\n\n'), () => {}), /源连接失败/)
  await assert.rejects(readJsonSse(new Response('{"detail":"无权限"}', { status: 403 }), () => {}), /无权限/)
})

test('draft edits invalidate previous review, hydration, and publication state', () => {
  memory.clear(); setActivePinia(createPinia())
  globalThis.builderTestAuth.user = { id: 'account-a' }
  const store = useBuilderStore()
  const session = store.createSession({ ontologyName: '设备', buildMethod: 'manual', ontologyId: 'oa' })
  const object = { id: 'o', name: 'Device', displayName: '设备', tier: 2, description: '', primaryKey: 'id', icon: '◉', instanceCount: 0, properties: [{ id: 'p', name: 'risk', displayName: '风险', type: 'number', required: false }], derivedProperties: [], actions: [], approved: false }
  store.updateSession(session.sessionId, { ontologyObjects: [object] })
  store.approveAllObjects()
  const fingerprint = builderContentSignature(store.activeSession)
  store.updateSession(session.sessionId, { status: 'published', drillResult: { phases: [] }, drillStatus: 'pass', drillFingerprint: fingerprint, publishedVersion: 'v1' })
  store.updateObject('o', { description: '当前定义已修改' })
  assert.equal(store.activeSession.drillResult, undefined)
  assert.equal(store.activeSession.publishedVersion, undefined)
  assert.equal(store.activeSession.ontologyObjects[0].approved, false)
  assert.equal(store.activeSession.status, 'drafting')
  store.approveAllObjects()
  assert.equal(store.activeSession.ontologyObjects[0].approved, true)
  globalThis.builderTestAuth.user = { id: 'account-b' }
  assert.equal(store.activeSession, null)
})

test('builder sessions isolate target ontology, build entry, and account', () => {
  const session = { ontologyId: 'oa', builderKind: 'document', buildMethod: 'chat', ownerId: 'a', status: 'drafting' }
  assert.equal(matchesBuilderSession(session, 'document', 'oa', 'a'), true)
  assert.equal(matchesBuilderSession(session, 'asset', 'oa', 'a'), false)
  assert.equal(matchesBuilderSession(session, 'document', 'ob', 'a'), false)
  assert.equal(matchesBuilderSession(session, 'document', 'oa', 'b'), false)
  assert.equal(matchesBuilderSession({ ...session, ownerId: undefined }, 'document', 'oa', 'b'), false)
})


test('monitor reconnects with current account credentials and ignores obsolete sockets', async () => {
  const instances = []
  class Socket {
    static OPEN = 1; static CONNECTING = 0
    readyState = 0
    constructor(url, protocols) { this.url = url; this.protocols = protocols; instances.push(this) }
    close() { this.readyState = 3; this.onclose?.() }
    send() {}
  }
  globalThis.WebSocket = Socket
  globalThis.window = { location: { origin:'http://localhost' } }
  globalThis.builderTestAuth.token = 'account-a-token'
  let source = readFileSync(new URL('../src/composables/useMonitorWS.ts',import.meta.url),'utf8')
    .replace("'vue'", JSON.stringify(import.meta.resolve('vue')))
    .replace("import { useAuthStore } from '../store/auth'", 'const useAuthStore = () => globalThis.builderTestAuth')
    .replace('import.meta.env.VITE_API_BASE_URL', 'undefined')
  const { useMonitorWS } = await import(moduleUrl(source))
  const renderer = createRenderer({ patchProp(){}, insert(){}, remove(){}, createElement(){return {}}, createText(){return {}}, createComment(){return {}}, setText(){}, setElementText(){}, parentNode(){return null}, nextSibling(){return null} })
  let monitor
  const app = renderer.createApp({ setup() { monitor = useMonitorWS(); return () => null } })
  app.mount({})
  const old = instances[0]
  assert.deepEqual(old.protocols,['ontology-monitor','jwt.account-a-token'])
  old.readyState = 1; old.onopen()
  old.onmessage({data:JSON.stringify({type:'alert',data:{id:'a-alert'}})})
  assert.equal(monitor.alerts.value.length,1)
  globalThis.builderTestAuth.token = 'account-b-token'
  await nextTick()
  const current = instances[1]
  assert.equal(old.readyState,3)
  assert.deepEqual(current.protocols,['ontology-monitor','jwt.account-b-token'])
  assert.equal(monitor.alerts.value.length,0)
  old.onmessage({data:JSON.stringify({type:'alert',data:{id:'late-a-alert'}})})
  old.onerror()
  assert.equal(monitor.alerts.value.length,0)
  assert.equal(current.readyState,0)
  globalThis.builderTestAuth.token = ''
  await nextTick()
  assert.equal(current.readyState,3)
  assert.equal(instances.length,2)
  app.unmount()
})


test('system event subscriptions restore audit history, preserve split frames and reset on account changes', async () => {
  const previousFetch = globalThis.fetch
  const connections=[]
  globalThis.builderTestAuth.token='event-a-token'
  globalThis.builderTestAuth.hasPermission = () => true
  globalThis.systemHistoryFixture=async () => ({items:[{id:'audit-'+globalThis.builderTestAuth.token,timestamp:'2026-10-11T00:00:00Z',target_type:'system_config',user_name:'审查',action:'update',target_name:'设置',status:'success'}]})
  globalThis.fetch=async (_url, options) => {
    let sink
    const body=new ReadableStream({start(controller){sink=controller},cancel(){}})
    const connection={sink,signal:options.signal}; connections.push(connection)
    options.signal.addEventListener('abort',()=> {try{sink.error(new DOMException('cancelled','AbortError'))}catch{/* already closed */}})
    return new Response(body,{status:200})
  }
  let source=readFileSync(new URL('../src/composables/useSystemEvents.ts',import.meta.url),'utf8')
    .replace("'vue'",JSON.stringify(import.meta.resolve('vue')))
    .replace("import { get } from '../api/client'",'const get = (...args) => globalThis.systemHistoryFixture(...args)')
    .replace("import { authHeaders } from '../utils/authHeaders'",'const authHeaders = () => ({})')
    .replace("import { useAuthStore } from '../store/auth'",'const useAuthStore = () => globalThis.builderTestAuth')
    .replace("'../components/logic/sseDecoder'",JSON.stringify(decoderUrl))
    .replace('import.meta.env.VITE_API_BASE_URL','undefined')
  const { useSystemEvents }=await import(moduleUrl(source))
  const renderer=createRenderer({patchProp(){},insert(){},remove(){},createElement(){return {}},createText(){return {}},createComment(){return {}},setText(){},setElementText(){},parentNode(){return null},nextSibling(){return null}})
  let events
  const app=renderer.createApp({setup(){events=useSystemEvents();return ()=>null}})
  app.mount({})
  const settle=async()=> {await nextTick();await new Promise(resolve=>setTimeout(resolve,0))}
  try {
    await settle()
    assert.equal(events.connected.value,true)
    assert.equal(events.events.value[0].id,'audit-event-a-token')
    const bytes=new TextEncoder().encode('event: asset.created\r\ndata: {"event":"asset.created","event_id":"live","ts":1791676800000,"asset_name":"设备🙂"}\r\n\r\n')
    for (let i=0;i<bytes.length;i++) connections[0].sink.enqueue(bytes.slice(i,i+1))
    await settle()
    assert.equal(events.events.value[0].id,'live')
    assert.match(events.events.value[0].description,/设备🙂/)
    globalThis.builderTestAuth.token='event-b-token'
    await settle()
    assert.equal(connections[0].signal.aborted,true)
    assert.equal(events.events.value[0].id,'audit-event-b-token')
    assert.equal(events.events.value.some(event=>event.id==='live'),false)
    globalThis.builderTestAuth.hasPermission = () => false
    globalThis.systemHistoryFixture = async () => { throw new Error('Unauthorized history must not be queried') }
    globalThis.builderTestAuth.token = 'operator-token'
    await settle()
    assert.equal(connections.length, 3)
    assert.equal(events.connected.value, true)
    assert.deepEqual(events.events.value, [])
    connections[2].sink.enqueue(new TextEncoder().encode('data: invalid-json\n\n'))
    await settle()
    assert.equal(events.connected.value,false)
    assert.match(events.error.value,/JSON|Unexpected/)
  } finally { app.unmount();globalThis.fetch=previousFetch;globalThis.builderTestAuth.token='';delete globalThis.systemHistoryFixture }
  assert.equal(connections[2].signal.aborted,true)
})


test('account switch clears shared store caches and discards late source responses', async () => {
  globalThis.builderTestAuth.user={id:'cache-account-a'}
  setActivePinia(createPinia())
  const imported=[]
  for (const kind of ['asset','connection','scenarios','ontology']) {
    let resolveRequest
    const pending=new Promise(resolve=>{resolveRequest=resolve})
    globalThis.cacheApiFixture={listAssets:()=>pending,listConnections:()=>pending,list:()=>pending}
    let source=readFileSync(new URL(`../src/store/${kind}.ts`,import.meta.url),'utf8')
      .replace("'vue'",JSON.stringify(import.meta.resolve('vue')))
      .replace("'pinia'",JSON.stringify(import.meta.resolve('pinia')))
      .replace("import { useAuthStore } from './auth'",'const useAuthStore = () => globalThis.builderTestAuth')
      .replace(/import \* as api from '..\/api\/(asset|connection)'/,'const api = globalThis.cacheApiFixture')
      .replace("import { scenarioApi, type Scenario } from '../api/scenarios'",'const scenarioApi = globalThis.cacheApiFixture')
      .replace("import { entityApi } from '../api/ontology'",'const entityApi = globalThis.cacheApiFixture')
    const exports=await import(moduleUrl(source))
    const store=Object.values(exports)[0]()
    const operation=kind==='scenarios'?store.fetchScenarios():kind==='ontology'?store.fetchEntities():store.fetchList()
    imported.push(store)
    globalThis.builderTestAuth.user={id:'cache-account-'+kind}
    resolveRequest([{id:'stale-account-a',name:'old'}])
    await operation
    const rows=kind==='scenarios'?store.scenarios:kind==='ontology'?store.entities:store.items
    assert.deepEqual(rows,[])
    if (kind==='scenarios') assert.equal(store.loaded,false)
    if (kind==='ontology') assert.equal(store.currentOntologyId,null)
  }
  delete globalThis.cacheApiFixture
})


test('real action correlation survives refresh without caching inputs and prevents uncertain replay', async () => {
  memory.clear()
  const {ensureActionAttempt,readActionAttempt,saveActionAttempt,clearCompletedActionAttempt} = await import(moduleUrl(readFileSync(new URL('../src/utils/actionAttempt.ts',import.meta.url),'utf8')))
  const first=ensureActionAttempt('owner-a','action-a')
  assert.match(first.key,/^ui-[0-9a-f]{32}$/)
  assert.equal(ensureActionAttempt('owner-a','action-a').key,first.key)
  assert.equal(readActionAttempt('owner-b','action-a'),null)
  assert.notEqual(ensureActionAttempt('owner-a','action-b').key,first.key)
  saveActionAttempt('owner-a','action-a',{...first,state:'unknown',execution_id:'receipt',params:{credential:'never-cache'}})
  assert.throws(()=>clearCompletedActionAttempt('owner-a','action-a'),/尚未确定/)
  assert.equal(ensureActionAttempt('owner-a','action-a').key,first.key)
  assert.equal([...memory.values()].join('').includes('credential'),false)
  saveActionAttempt('owner-a','action-a',{...first,state:'succeeded',execution_id:'receipt'})
  clearCompletedActionAttempt('owner-a','action-a')
  assert.notEqual(ensureActionAttempt('owner-a','action-a').key,first.key)
})


async function mountLogicEditor(filename, expose) {
  let source=readFileSync(new URL(`../src/components/logic/${filename}.vue`,import.meta.url),'utf8')
    .replace('</script>',`defineExpose({${expose}})\n</script>`)
  const descriptor=parse(source,{filename:`${filename}.vue`}).descriptor
  source=compileScript(descriptor,{id:`review-${filename}`}).content
    .replaceAll("'vue'",JSON.stringify(import.meta.resolve('vue')))
    .replace(/import \{ useProductText \} from[^\n]+/, 'const useProductText = () => ({text:value=>value})')
    .replace(/import \{ useManagementPermission \} from[^\n]+/, 'const useManagementPermission = () => ({canEdit:globalThis.logicEditorFixture.canEdit})')
    .replace(/import \{ useRoute, useRouter \} from[^\n]+/, 'const useRoute = () => ({query:{}}); const useRouter = () => ({push(){}})')
    .replace(/import \{ actionApi[^\n]+/, 'const actionApi = globalThis.logicEditorFixture.actionApi')
    .replace(/import \{ functionApi[^\n]+/, 'const functionApi = globalThis.logicEditorFixture.functionApi')
    .replace(/import \{ entityApi[^\n]+/, 'const entityApi = globalThis.logicEditorFixture.entityApi')
    .replace(/import AiCodePanel[^\n]+/, 'const AiCodePanel = {}')
    .replace(/import \{ useOntologyStore \} from[^\n]+/, 'const useOntologyStore = () => ({currentOntologyId:"oa"})')
    .replace(/import \{ useToast \} from[^\n]+/, 'const useToast = () => ({info(){},error(){},success(){}})')
    .replace(/import \{ randomUUID \} from[^\n]+/, 'const randomUUID = () => "editor-test"')
  const component=(await import(moduleUrl(source))).default
  component.render=()=>null
  const renderer=createRenderer({patchProp(){},insert(){},remove(){},createElement(){return {}},createText(){return {}},createComment(){return {}},setText(){},setElementText(){},parentNode(){return null},nextSibling(){return null}})
  const app=renderer.createApp(component,{visible:true,editId:'logic'})
  const editor=app.mount({})
  for(let attempt=0;attempt<24&&(!editor.savedId||editor.hasUnsavedChanges);attempt++) await nextTick()
  assert.equal(editor.savedId,'logic')
  return {app,editor}
}

test('actual Action editor previews saved definitions, invalidates stale replies, and persists parameter removal', async () => {
  let dispatch,complete,payload
  globalThis.alert=()=>{}
  globalThis.logicEditorFixture={canEdit:ref(true),entityApi:{list:async()=>[{id:'device'}],detail:async()=>({attributes:[{id:'temperature-attr',name:'temperature',type:'number'}]})},actionApi:{
    types:async()=>[{type_key:'custom_script',config_schema:{script:{type:'string'}}}],
    detail:async()=>({id:'logic',name:'Risk',ontology_id:'ob',category:'system',status:'active',action_type:'custom_script',parameters_json:[{name:'temperature',type:'number',required:true,entity_attribute_id:'temperature-attr'}],type_config:{script:'def run(params): return params'}}),
    execute:async(...args)=>{dispatch=args;return await new Promise(resolve=>{complete=resolve})},
    update:async(id,values)=>{payload=values;return {id,name:values.name}},
  }}
  const {app,editor}=await mountLogicEditor('ActionBuilderDrawer','form,typeConfigValues,testInput,testResult,savedId,runTest,save,hasUnsavedChanges')
  try {
    editor.testInput='{"temperature":92}'
    const running=editor.runTest()
    assert.equal(dispatch[2],true,'preview must never send business side effects')
    editor.typeConfigValues.script='def run(params): return 0'
    complete({success:true,message:'old result'});await running
    assert.equal(editor.testResult,null,'editing during a request must discard old preview')
    assert.equal(editor.hasUnsavedChanges,true)
    dispatch=null;await editor.runTest();assert.equal(dispatch,null,'unsaved draft must not test server old code')
    await editor.save()
    assert.deepEqual(payload.output_schema,[])
    assert.equal(payload.ontology_id,'ob','global editing must preserve the component owning ontology')
    assert.equal(payload.parameters_json[0].entity_attribute_id,'temperature-attr')
    assert.equal('attribute_id' in payload.parameters_json[0],false)
    editor.form.output_schema_json='[{"name":"risk","type":"number"}]'
    editor.form.parameters=[];editor.form.description=''
    await editor.save()
    assert.deepEqual(payload.parameters_json,[])
    assert.deepEqual(payload.output_schema,[{name:'risk',type:'number'}])
    assert.equal(payload.entity_id,null)
    assert.equal(payload.description,'')
    assert.equal(editor.hasUnsavedChanges,false)
    editor.testInput='{}';const fresh=editor.runTest();complete({success:true,message:'current preview'});await fresh
    assert.match(editor.testResult,/current preview/)
    editor.testInput='{"temperature":1}';assert.equal(editor.testResult,null)
  } finally {app.unmount();delete globalThis.logicEditorFixture;delete globalThis.alert}
})

test('actual Function editor rejects unsaved tests and discards results when code changes in flight', async () => {
  let dispatch=0,complete
  globalThis.logicEditorFixture={canEdit:ref(true),entityApi:{list:async()=>[]},functionApi:{
    detail:async()=>({id:'logic',name:'Risk',callable_name:'risk',description:'',entity_ids:[],return_type:'number',tags:[],input_schema:[],logic_type:'expression',logic_body:'temperature / 100'}),
    test:async()=>{dispatch++;return await new Promise(resolve=>{complete=resolve})},
    update:async(id,values)=>({id,name:values.name}),
  }}
  const {app,editor}=await mountLogicEditor('FunctionBuilderDrawer','form,testInput,testResult,testSimulated,testSuccess,savedId,runTest,save,hasUnsavedChanges')
  try {
    editor.testInput='{"temperature":92}'
    const old=editor.runTest();assert.equal(dispatch,1)
    editor.form.logic_body='temperature / 50';complete({success:true,result:0.92});await old
    assert.equal(editor.testResult,null)
    await editor.runTest();assert.equal(dispatch,1)
    await editor.save();assert.equal(editor.hasUnsavedChanges,false)
    const current=editor.runTest();complete({success:true,result:1.84});await current
    assert.equal(editor.testResult,'1.84')
    const preview=editor.runTest();complete({success:true,result:null,outcome:'simulated',simulated:true,requested_write:{entity_name:'Device',record_id:'D-1',updates:{status:'maintenance'}}});await preview
    assert.equal(editor.testSimulated,true);assert.equal(editor.testSuccess,false)
    assert.deepEqual(JSON.parse(editor.testResult),{entity_name:'Device',record_id:'D-1',updates:{status:'maintenance'}})
    editor.form.logic_body='0';assert.equal(editor.testResult,null)
  } finally {app.unmount();delete globalThis.logicEditorFixture}
})

test('actual mapping editor requires explicit enrichment columns and invalidates prior approval', async () => {
  setActivePinia(createPinia());globalThis.builderTestAuth.user={id:'mapping-account'}
  const store=useBuilderStore(),session=store.createSession({ontologyName:'设备',buildMethod:'manual',ontologyId:'oa'})
  const object={id:'device',name:'Device',displayName:'设备',properties:[{id:'id',name:'id',type:'string',source_asset_id:'primary',source_column:'device_id'}],backing_asset_ids:['primary'],primaryKey:'id'}
  store.updateSession(session.sessionId,{ontologyObjects:[object]});store.approveAllObjects()
  let source=readFileSync(new URL('../src/views/builder/components/Step3Mapping.vue',import.meta.url),'utf8').replace('</script>','defineExpose({allMapped,bindTable,setEnrichments,setJoin,onPropertyAssetChange,assetTree})\n</script>')
  source=compileScript(parse(source).descriptor,{id:'mapping-regression'}).content
    .replaceAll("'vue'",JSON.stringify(import.meta.resolve('vue')))
    .replace(/import \{ message \} from[^\n]+/,'const message={warning(){},success(){},error(){}}')
    .replace(/import \{ useBuilderStore \} from[^\n]+/,'const useBuilderStore=()=>globalThis.mappingStore')
    .replace(/import \{ authHeaders \} from[^\n]+/,'const authHeaders=()=>({})')
    .replace(/import \{ fetchAssetTree, suggestColumns \} from[^\n]+/,'const fetchAssetTree=async()=>({tree:globalThis.mappingTree});const suggestColumns=async()=>({suggestions:[]})')
  globalThis.mappingStore=store;globalThis.mappingTree=[{connection_id:'source',connection_name:'隔离',tables:[{asset_id:'primary',table_name:'devices',columns:[{name:'device_id'}]},{asset_id:'owners',table_name:'owners',columns:[{name:'serial'},{name:'owner'}]}]}]
  const component=(await import(moduleUrl(source))).default;component.render=()=>null
  const renderer=createRenderer({patchProp(){},insert(){},remove(){},createElement(){return {}},createText(){return {}},createComment(){return {}},setText(){},setElementText(){},parentNode(){return null},nextSibling(){return null}})
  const app=renderer.createApp(component,{session:store.activeSession});const editor=app.mount({})
  try {
    await nextTick();await new Promise(resolve=>setTimeout(resolve,0))
    const current=store.activeSession.ontologyObjects[0]
    assert.equal(editor.allMapped,true)
    editor.setEnrichments(current,['owners']);assert.equal(editor.allMapped,false)
    assert.equal(store.activeSession.ontologyObjects[0].approved,false)
    editor.setJoin(current,'owners','primary_source_column','device_id');assert.equal(editor.allMapped,false)
    editor.setJoin(current,'owners','enrichment_source_column','serial');assert.equal(editor.allMapped,true)
    await editor.bindTable('device',globalThis.mappingTree[0].tables[0]);assert.deepEqual(current.backing_asset_ids,['primary','owners'])
    editor.setJoin(current,'owners','enrichment_source_column','missing');assert.equal(editor.allMapped,false)
    editor.setEnrichments(current,[]);assert.equal(editor.allMapped,true);assert.deepEqual(current.enrichment_bindings,[])
    editor.onPropertyAssetChange(current.properties[0],'owners');assert.equal(editor.allMapped,false);assert.equal(current.properties[0].source_column,undefined)
  } finally {app.unmount();delete globalThis.mappingStore;delete globalThis.mappingTree}
})

test('actual Agent recovery UI requires human evidence and resumes only the remaining graph', async () => {
  let observed=[],resolveLate,resolveHistory
  globalThis.agentRecoveryFixture={
    listConversations:async()=>[],
    getConversation:async()=>new Promise(resolve=>{resolveHistory=resolve}),
    reconcileAction:async(...args)=>{observed.push(['reconcile',...args]);return {status:'approved',summary:'人工核查已确认',result:{continuation_status:'awaiting_resume',manual_reconciliation:{evidence:args[2].evidence}}}},
    resumeAction:async(...args)=>{observed.push(['resume',...args]);return {status:'approved',result:{continuation_status:'completed'}}},
    confirmAction:async()=>new Promise(resolve=>{resolveLate=resolve}),
  }
  let source=readFileSync(new URL('../src/views/agents/components/AgentChatPanel.vue',import.meta.url),'utf8').replace('</script>','defineExpose({recoverAction,reconcileForm,decide,selectConversation,messages,error,deciding})\n</script>')
  source=compileScript(parse(source).descriptor,{id:'agent-recovery-regression'}).content
    .replaceAll("'vue'",JSON.stringify(import.meta.resolve('vue')))
    .replace(/import \{[^}]*\} from '\.\.\/\.\.\/\.\.\/api\/agents';?/,'const agentsApi=globalThis.agentRecoveryFixture')
    .replace(/import \{ readJsonSse \} from[^\n]+/,'const readJsonSse=()=>{}')
    .replace(/import \{ formatPlatformDateTime \} from[^\n]+/,'const formatPlatformDateTime=value=>value')
    .replace(/import \{ authHeaders \} from[^\n]+/,'const authHeaders=()=>({})')
    .replace(/import \{ renderMarkdownSafe \} from[^\n]+/,'const renderMarkdownSafe=value=>value')
    .replace(/import \{ copyText, downloadHtml, looksLikeMarkdown \} from[^\n]+/,'const copyText=async()=>true,downloadHtml=()=>{},looksLikeMarkdown=()=>false')
  const component=(await import(moduleUrl(source))).default;component.render=()=>null
  const renderer=createRenderer({patchProp(){},insert(){},remove(){},createElement(){return {}},createText(){return {}},createComment(){return {}},setText(){},setElementText(){},parentNode(){return null},nextSibling(){return null}})
  const props=reactive({agentId:'agent-a',agentName:'审核',dirty:false,canAuthorize:true,canConfirmActions:true,actionMode:'confirm'})
  let editor
  const app=renderer.createApp({setup(){return ()=>h(component,{...props,ref:value=>{editor=value}})}})
  app.mount({});await nextTick()
  const pending={pending_id:'pending',action_name:'真实动作',params:{},status:'unknown',result:{outcome:'unknown'}}
  try {
    await editor.recoverAction(pending,false);assert.equal(observed.length,0);assert.match(editor.error,/至少10字/)
    Object.assign(editor.reconcileForm('pending'),{acknowledged:true,evidence:'已从真实源表回读状态maintenance',receipt_id:'receipt-123'})
    await editor.recoverAction(pending,false);assert.equal(observed[0][0],'reconcile');assert.equal(observed[0][2],'pending');assert.equal(pending.status,'approved');assert.equal(pending.result.continuation_status,'awaiting_resume')
    props.dirty=true;await nextTick();await editor.recoverAction(pending,true);assert.equal(observed.length,1)
    props.dirty=false;props.canConfirmActions=false;await nextTick()
    await editor.decide(pending,true);await editor.recoverAction(pending,false);assert.equal(observed.length,1,'strategy execution must not approve business actions')
    await editor.recoverAction(pending,true);assert.equal(observed[1][0],'resume');assert.equal(pending.result.continuation_status,'completed')
    props.canConfirmActions=true;await nextTick()
    const late=editor.decide(pending,true);props.agentId='agent-b';await nextTick();resolveLate({status:'failed',result:{error:'late account A'}});await late
    assert.equal(pending.status,'approved');assert.equal(editor.deciding,'')
    const history=editor.selectConversation('old-history');props.agentId='agent-c';await nextTick();resolveHistory({messages:[{role:'assistant',content:'Account B private'}]});await history;assert.deepEqual(editor.messages,[])
    props.canAuthorize=false;await nextTick();await editor.recoverAction(pending,true);assert.equal(observed.length,2)
  } finally {app.unmount();delete globalThis.agentRecoveryFixture}
})


test('actual Action recovery UI never dispatches unknown outcomes and requires an acknowledged receipt', async()=>{
  memory.clear();let dispatches=0,reconciliations=[]
  const attempts=await import(moduleUrl(readFileSync(new URL('../src/utils/actionAttempt.ts',import.meta.url),'utf8')))
  globalThis.actionRecoveryFixture={auth:reactive({user:{id:'action-owner'}}),permission:{canEdit:ref(true),canExecute:ref(true)},api:{
    list:async()=>[],types:async()=>[],execute:async()=>{dispatches++;return {success:true}},
    executionByKey:async()=>({execution_id:'journal-1',state:'unknown',params:{device_id:'DEV-001'},success:false}),
    reconcile:async(...args)=>{reconciliations.push(args);return {execution_id:'journal-1',state:'succeeded',success:true,output:{manual_reconciliation:{evidence:args[2].evidence}}}},
  },attempts}
  let source=readFileSync(new URL('../src/views/logic/ActionsView.vue',import.meta.url),'utf8').replace('</script>','defineExpose({openExecution,handleExecute,reconcileExecution,executionStateLabel,executionError,executionResult,executionAttempt,reconciliationAcknowledged,reconciliationEvidence,reconciliationReceipt})\n</script>')
  source=compileScript(parse(source).descriptor,{id:'action-recovery-regression'}).content.replace(/import[\s\S]*? from ['"]([^'"]+)['"];?/g,(full,location)=>{
    if(location==='vue')return full.replace("'vue'",JSON.stringify(import.meta.resolve('vue')))
    if(location.endsWith('.vue'))return 'const '+full.match(/import\s+(\w+)\s+from/)[1]+'={}'
    if(location.includes('useManagementPermission'))return 'const useManagementPermission=()=>globalThis.actionRecoveryFixture.permission'
    if(location.includes('useProductText'))return 'const useProductText=()=>({text:value=>value})'
    if(location==='vue-router')return 'const useRoute=()=>({params:{},query:{}}),useRouter=()=>({push(){}})'
    if(location.includes('api/actions'))return 'const actionApi=globalThis.actionRecoveryFixture.api'
    if(location.includes('store/auth'))return 'const useAuthStore=()=>globalThis.actionRecoveryFixture.auth'
    if(location.includes('store/ontology'))return 'const useOntologyStore=()=>({currentOntologyId:null})'
    if(location.includes('store/scenarios'))return 'const useScenarioStore=()=>({refreshScenarios:async()=>{}})'
    if(location.includes('useToast'))return 'const useToast=()=>({error(){},success(){},warning(){}})'
    if(location.includes('api/skills'))return "const skillError=(error,fallback)=>error.message||fallback"
    if(location.includes('actionAttempt'))return 'const {readActionAttempt,ensureActionAttempt,saveActionAttempt,clearCompletedActionAttempt}=globalThis.actionRecoveryFixture.attempts'
    return ''
  })
  const component=(await import(moduleUrl(source))).default;component.render=()=>null
  const renderer=createRenderer({patchProp(){},insert(){},remove(){},createElement(){return {}},createText(){return {}},createComment(){return {}},setText(){},setElementText(){},parentNode(){return null},nextSibling(){return null}})
  const app=renderer.createApp(component);const editor=app.mount({})
  try{
    attempts.saveActionAttempt('action-owner','action-1',{key:'original-key',state:'unknown',execution_id:'journal-1'})
    editor.openExecution({id:'action-1',name:'动作',status:'active',parameters_json:[]})
    await nextTick();await new Promise(resolve=>setTimeout(resolve,0))
    assert.equal(editor.executionResult.state,'unknown');await editor.handleExecute();assert.equal(dispatches,0)
    await editor.reconcileExecution();assert.equal(reconciliations.length,0);assert.match(editor.executionError,/至少10字/)
    editor.reconciliationAcknowledged=true;editor.reconciliationEvidence='独立源表回读已确认DEV-001状态maintenance';editor.reconciliationReceipt='receipt-1'
    await editor.reconcileExecution();assert.equal(reconciliations[0][1],'journal-1');assert.equal(reconciliations[0][2].receipt_id,'receipt-1')
    assert.equal(attempts.readActionAttempt('action-owner','action-1').key,'original-key');assert.equal(editor.executionResult.state,'succeeded');assert.equal(dispatches,0)
    assert.match(editor.executionStateLabel({state:'committed_unrecorded'}),/已提交/)
    editor.executionResult={state:'partial_committed',success:false};await editor.handleExecute();assert.equal(dispatches,0)
    assert.match(editor.executionStateLabel({state:'partial_committed'}),/写入保留/)
  }finally{app.unmount();delete globalThis.actionRecoveryFixture}
})


test('all shared reads wait for restored identity and never continue an old caller as a new account', async () => {
  for (const kind of ['asset','connection','scenarios','ontology']) {
    setActivePinia(createPinia())
    let finish,calls=0
    const auth=reactive({token:'restore-a',user:null,fetchUser:()=>new Promise(resolve=>{finish=resolve})})
    globalThis.restoreStoreFixture={auth,api:{listAssets:async()=>{calls++;return [{id:'restored-row'}]},listConnections:async()=>{calls++;return [{id:'restored-row'}]},list:async()=>{calls++;return [{id:'restored-row',code:'restored'}]}}}
    let source=readFileSync(new URL(`../src/store/${kind}.ts`,import.meta.url),'utf8')
      .replace("'vue'",JSON.stringify(import.meta.resolve('vue'))).replace("'pinia'",JSON.stringify(import.meta.resolve('pinia')))
      .replace("import { useAuthStore } from './auth'",'const useAuthStore = () => globalThis.restoreStoreFixture.auth')
      .replace(/import \* as api from '..\/api\/(asset|connection)'/,'const api = globalThis.restoreStoreFixture.api')
      .replace("import { scenarioApi, type Scenario } from '../api/scenarios'",'const scenarioApi = globalThis.restoreStoreFixture.api')
      .replace("import { entityApi } from '../api/ontology'",'const entityApi = globalThis.restoreStoreFixture.api')
    const store=Object.values(await import(moduleUrl(source)))[0]()
    const read=()=>kind==='scenarios'?store.fetchScenarios(true):kind==='ontology'?store.switchOntology('ontology-a'):store.fetchList()
    const first=read();assert.equal(calls,0,kind+' must not request data before identity recovery')
    auth.user={id:'restore-owner-a'};finish();await first
    assert.equal(calls,1);assert.equal((kind==='scenarios'?store.scenarios:kind==='ontology'?store.entities:store.items)[0].id,'restored-row')
    if(kind==='ontology')assert.equal(store.currentOntologyId,'ontology-a')
    auth.user=null;const failed=read();finish();await failed;assert.equal(calls,1,'failed identity recovery must not fetch business data')
    const changed=read();auth.token='restore-b';auth.user={id:'restore-owner-b'};finish();await changed;assert.equal(calls,1,'old caller cannot start a request with new account credentials')
    auth.user=null;const loggedOut=read();auth.token=null;finish();await loggedOut;assert.equal(calls,1,'logout during recovery must cancel the pending read')
  }
  delete globalThis.restoreStoreFixture
})


test('actual app waits for recovery, preserves the mounted page and offers retry after recovery failure', async () => {
  let finish,mounts=0
  const auth=reactive({token:'restore-token',user:null,fetchUser:()=>new Promise(resolve=>{finish=resolve})})
  globalThis.restoreAppFixture={auth,platform:reactive({language:'zh-CN',system_name:'平台',load:async()=>{}}),route:reactive({path:'/ontology/list/test',meta:{title:'本体详情'}})}
  globalThis.document={title:''}
  let source=readFileSync(new URL('../src/App.vue',import.meta.url),'utf8')
    .replace('</script>','defineExpose({restoreSession,restoringSession,restoreError})\n</script>')
  source=compileScript(parse(source).descriptor,{id:'restore-app-regression',inlineTemplate:true}).content
    .replace(/import[\s\S]*? from ['"]([^'"]+)['"];?/g,(full,location)=>{
      if(location==='vue')return full.replace(/['"]vue['"]/,JSON.stringify(import.meta.resolve('vue')))
      if(location.includes('useProductText'))return 'const useProductText=()=>({text:value=>value})'
    if(location==='vue-router')return 'const useRoute=()=>globalThis.restoreAppFixture.route'
      if(location==='vue-i18n')return 'const useI18n=()=>({t:key=>key})'
      if(location.includes('store/auth'))return 'const useAuthStore=()=>globalThis.restoreAppFixture.auth'
      if(location.includes('store/platformConfig'))return 'const usePlatformConfigStore=()=>globalThis.restoreAppFixture.platform'
      if(location.includes('store/theme'))return 'const useThemeStore=()=>({isDark:false,init(){}})'
      if(location==='ant-design-vue')return 'const theme={defaultAlgorithm:{},darkAlgorithm:{}}'
      if(location.includes('ant-design-vue/es/locale/zh_CN'))return 'const zhCN={}'
      if(location.includes('ant-design-vue/es/locale/en_US'))return 'const enUS={}'
      if(location.includes('platformPresentation'))return 'const platformRouteTitle=value=>value'
      if(location.includes('utils/access'))return 'const canAccessRoute=()=>true'
      const name=full.match(/import (\w+) from/)?.[1];return name?'const '+name+'={render:()=>null}':''
    })
  const component=(await import(moduleUrl(source))).default
  const remove=child=>{const parent=child.parent;if(parent){const index=parent.children.indexOf(child);if(index>=0)parent.children.splice(index,1)};child.parent=null}
  const renderer=createRenderer({patchProp(){},insert(child,parent,anchor){remove(child);parent.children??=[];child.parent=parent;const index=anchor?parent.children.indexOf(anchor):-1;parent.children.splice(index<0?parent.children.length:index,0,child)},remove,createElement:()=>({children:[]}),createText:()=>({children:[]}),createComment:()=>({children:[]}),setText(){},setElementText(){},parentNode:child=>child.parent,nextSibling:child=>child.parent?.children[child.parent.children.indexOf(child)+1]||null})
  const app=renderer.createApp(component)
  const Page={setup(){mounts++;return()=>h('p','Actual protected page')}}
  const routerStub={setup(_props,{slots}){return()=>slots.default?.({Component:Page})}}
  const providerStub={inheritAttrs:false,setup(_props,{slots}){return()=>slots.default?.()}}
  app.component('RouterView',routerStub)
  app.component('AConfigProvider',providerStub)
  const shell=app.mount({})
  try {
    assert.equal(shell.restoringSession,true);assert.equal(mounts,0)
    finish();await nextTick();await nextTick()
    assert.equal(shell.restoringSession,false);assert.equal(shell.restoreError,true);assert.equal(mounts,0,'failed recovery must not mount a page without identity')
    const retry=shell.restoreSession();assert.equal(shell.restoringSession,true)
    auth.user={id:'restored-user'};finish();await retry;await nextTick()
    assert.equal(shell.restoreError,false);assert.equal(mounts,1)
    await nextTick();assert.equal(mounts,1,'initial identity resolution must not reset page interactions')
  }finally{app.unmount();delete globalThis.restoreAppFixture;delete globalThis.document}
})


async function builderComponent(filename, expose, fixture) {
  let source=readFileSync(new URL(`../src/views/builder/${filename}.vue`,import.meta.url),'utf8').replace('</script>',`defineExpose({${expose}})\n</script>`)
  source=compileScript(parse(source).descriptor,{id:'fix-'+filename}).content.replace(/import[\s\S]*? from ['"]([^'"]+)['"];?/g,(full,location)=>{
    if(location==='vue'||location==='pinia')return full.replace(/["'](?:vue|pinia)["']/,JSON.stringify(import.meta.resolve(location)))
    if(location.includes('useProductText'))return 'const useProductText=()=>({text:value=>value})'
    if(location==='vue-router')return 'const useRoute=()=>globalThis.builderFixFixture.route,useRouter=()=>({push(){}})'
    if(location.includes('store/auth'))return 'const useAuthStore=()=>globalThis.builderTestAuth'
    if(location.includes('store/builder'))return 'const useBuilderStore=()=>globalThis.builderFixFixture.store'
    if(location.includes('store/owlEditor'))return 'const useOwlEditorStore=()=>({setScope(){},saveDraft(){},exportOwlXml(){return "<Ontology/>"}})'
    if(location.includes('utils/builderSession'))return `import { matchesBuilderSession,builderContentSignature } from ${JSON.stringify(signatureUrl)}`
    if(location.includes('api/ontologyPublish'))return 'const ontologyPublishApi={quickPublish:(...args)=>globalThis.builderFixFixture.publish(...args)}'
    if(location.includes('api/client'))return 'const captureAuthSession=()=>({id:globalThis.builderTestAuth.user?.id}),post=(...args)=>globalThis.builderFixFixture.finalize(...args)'
    if(location.includes('api/ontology'))return 'const entityApi={previewFile:()=>globalThis.builderFixFixture.preview()}'
    if(location.includes('useManagementPermission'))return 'const useManagementPermission=()=>({canEdit:ref(true)})'
    if(location.includes('platformTime'))return 'const formatPlatformTime=value=>String(value)'
    if(location.includes('store/scenarios'))return 'const useScenarioStore=()=>({fetchScenarios:async()=>{},scenarios:[],byCode:()=>null})'
    if(location.includes('api/sse'))return 'const readJsonSse=()=>{},postJsonSse=()=>{}'
    if(location.includes('data/builderPresets'))return `import {HYDRATION_PHASES,DEFAULT_PUBLISH_GATES} from ${JSON.stringify(moduleUrl(readFileSync(new URL('../src/data/builderPresets.ts',import.meta.url),'utf8')))}`
    if(location==='ant-design-vue')return 'const message={error(){},success(){},warning(){}}'
    return full.match(/^import\s+(\w+)\s+from/) ? 'const '+full.match(/^import\s+(\w+)\s+from/)[1]+'={}' : ''
  })
  globalThis.builderFixFixture=fixture
  const component=(await import(moduleUrl(source))).default;component.render=()=>null
  const renderer=createRenderer({patchProp(){},insert(){},remove(){},createElement(){return {}},createText(){return {}},createComment(){return {}},setText(){},setElementText(){},parentNode(){return null},nextSibling(){return null}})
  const app=renderer.createApp(component,fixture.props),editor=app.mount({});await nextTick()
  return {editor,app}
}

test('OWL bridge discards genuine delayed preview after target, account or mount changes',async()=>{
  for(const change of ['target','account','unmount']){
    memory.clear();setActivePinia(createPinia());globalThis.builderTestAuth.user={id:'owl-owner'}
    const store=useBuilderStore();const keep=store.createSession({ontologyName:'B',buildMethod:'manual',ontologyId:'B'});store.updateSession(keep.sessionId,{ontologyObjects:[{id:'b',name:'KeepB',properties:[]}]})
    const route=reactive({query:{ontology_id:'A'},path:'/builder'});let finish
    const {editor,app}=await builderComponent('OntologyBuilderView','bridgeEditor,editorMode,bridging',{route,store,preview:()=>new Promise(resolve=>{finish=resolve})})
    editor.editorMode='protege';await nextTick();const pending=editor.bridgeEditor()
    if(change==='target')route.query.ontology_id='B'
    if(change==='account')globalThis.builderTestAuth.user={id:'other-owner'}
    if(change==='unmount')app.unmount()
    await nextTick();finish({objects:[{name:'Device',properties:[]}],relations:[]});await pending
    assert.deepEqual(store.sessions.find(s=>s.ontologyId==='B').ontologyObjects.map(o=>o.name),['KeepB'])
    assert.equal(store.sessions.find(s=>s.ontologyId==='A').ontologyObjects.length,0)
    if(change!=='unmount')app.unmount()
  }
  delete globalThis.builderFixFixture
})

test('document keep imports the complete effective binding instead of rejected candidate columns',async()=>{
  memory.clear();setActivePinia(createPinia());globalThis.builderTestAuth.user={id:'doc-owner'};const store=useBuilderStore(),route=reactive({query:{ontology_id:'A'},path:'/builder/doc'})
  const {editor,app}=await builderComponent('DocBuilderView','onPersistDone,mappedResult,sessionId,step,steps',{route,store})
  try{
    editor.sessionId='document-session';editor.mappedResult={entities:[{name:'Device',primaryKey:'wrong_candidate',properties:[{name:'risk',field:'spare',type:'string'}]}],relations:[]}
    editor.onPersistDone([{entity_name:'Device',entity_id:'device',asset_id:'primary',primary_key:'id',backing_asset_ids:['primary','extra'],enrichment_bindings:[{asset_id:'extra',primary_source_column:'id',enrichment_source_column:'owner_id'}],field_mappings:[{attribute_id:'risk',attribute_name:'risk',source_asset_id:'primary',source_column:'risk_score',type:'number',required:true,transform:'value / 100',confidence:1},{attribute_id:'owner',attribute_name:'owner',source_asset_id:'extra',source_column:'owner_name',type:'string',required:false,confidence:1}]}])
    const draft=store.activeSession;assert.equal(draft.documentSessionId,'document-session');assert.equal(draft.ontologyObjects[0].primaryKey,'id')
    assert.deepEqual(draft.ontologyObjects[0].properties.map(p=>[p.name,p.source_asset_id,p.source_column,p.type]),[['risk','primary','risk_score','number'],['owner','extra','owner_name','string']])
    assert.equal(draft.ontologyObjects[0].properties[0].transform,'value / 100');assert.equal(draft.ontologyObjects[0].properties[0].required,true)
    assert.equal(editor.step,4,'effective mappings proceed to mapping verification before final review')
    assert.deepEqual(editor.steps.slice(4,6),['字段确认','最终审核'])
  }finally{app.unmount();delete globalThis.builderFixFixture}
})


test('navigation uses module permissions and accepts explicitly delegated administration', async () => {
  const {canAccessRoute,firstAccessibleRoute} = await import(moduleUrl(readFileSync(new URL('../src/utils/access.ts',import.meta.url),'utf8')))
  const permits = values => permission => values.includes(permission)
  assert.equal(canAccessRoute('/logic/functions',permits(['entity:read'])),false)
  assert.equal(canAccessRoute('/logic/functions',permits(['rule:read'])),true)
  assert.equal(canAccessRoute('/agent/manage',permits(['strategy:read'])),true)
  assert.equal(canAccessRoute('/agent/manage/new',permits(['strategy:read'])),false)
  assert.equal(canAccessRoute('/ops/config',permits(['admin:users'])),true)
  assert.equal(firstAccessibleRoute(permits(['strategy:read'])),'/agent/manage')
  assert.equal(firstAccessibleRoute(permits([])),'/forbidden')
})


test('publication sends the document receipt and cannot continue finalization as a different caller', async () => {
  for(const change of ['none','account','unmount']) {
    memory.clear();setActivePinia(createPinia());globalThis.builderTestAuth.user={id:'publisher-A'}
    const store=useBuilderStore();store.createSession({ontologyName:'A',ontologyId:'A',buildMethod:'chat',builderKind:'document'})
    store.updateSession(store.activeSession.sessionId,{documentSessionId:'document-receipt',ontologyObjects:[{id:'obj',name:'Device',properties:[],approved:true}]})
    store.approveAllObjects()
    store.updateSession(store.activeSession.sessionId,{drillResult:{phases:[],entityCount:1},drillStatus:'pass',drillFingerprint:builderContentSignature(store.activeSession)})
    let complete,publishes=0,body,signal
    const {app,editor}=await builderComponent('components/Step3Hydrate','confirmPublish,canPublish,success',{route:reactive({query:{ontology_id:'A'}}),store,props:{session:store.activeSession},finalize:async (_path,payload,config)=>{body=payload;signal=config.signal;return await new Promise(resolve=>complete=resolve)},publish:async()=>{publishes++;return {version_number:1}}})
    try {
      assert.equal(editor.canPublish,true)
      const pending=editor.confirmPublish();assert.equal(body.ontology_id,'A');assert.equal(body.document_session_id,'document-receipt')
      if(change==='account')globalThis.builderTestAuth.user={id:'publisher-B'}
      if(change==='unmount')app.unmount()
      complete({ontology_id:'A',created_entities:1,skipped:0});await pending
      assert.equal(publishes,change==='none'?1:0,'no second publication request after caller or component changes')
      if(change==='none')assert.equal(editor.success,true)
      if(change==='unmount')assert.equal(signal.aborted,true)
    }finally{if(change!=='unmount')app.unmount();delete globalThis.builderFixFixture}
  }
})


test('login creates a session identity on plain HTTP without crypto.randomUUID', async () => {
  const previousWindow=globalThis.window,cryptoDescriptor=Object.getOwnPropertyDescriptor(globalThis,'crypto')
  memory.clear();setActivePinia(createPinia())
  globalThis.window={addEventListener(){},dispatchEvent(){}}
  Object.defineProperty(globalThis,'crypto',{value:undefined,configurable:true})
  globalThis.httpLoginFixture={login:async()=>({token:'plain-http-token',refresh_token:'plain-http-refresh',user:{id:'http-user',permissions:[]}})}
  let source=readFileSync(new URL('../src/store/auth.ts',import.meta.url),'utf8').replace("'pinia'",JSON.stringify(import.meta.resolve('pinia'))).replace("'vue'",JSON.stringify(import.meta.resolve('vue'))).replace("import { authApi } from '../api/auth'",'const authApi=globalThis.httpLoginFixture').replace("'../utils/uuid'",JSON.stringify(moduleUrl(readFileSync(new URL('../src/utils/uuid.ts',import.meta.url),'utf8'))))
  try {
    const {useAuthStore}=await import(moduleUrl(source)),auth=useAuthStore()
    await auth.login({username:'user',password:'fixture'})
    assert.equal(auth.user.id,'http-user');assert.equal(auth.token,'plain-http-token')
    assert.match(memory.get('auth_session_id'),/^[0-9a-f-]{36}$/)
  }finally{if(cryptoDescriptor)Object.defineProperty(globalThis,'crypto',cryptoDescriptor);else delete globalThis.crypto;globalThis.window=previousWindow;delete globalThis.httpLoginFixture}
})
