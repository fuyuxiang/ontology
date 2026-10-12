import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { createPinia, setActivePinia } from 'pinia'
import { createRenderer, nextTick } from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'

function moduleUrl(source) {
  const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText
  return `data:text/javascript;base64,${Buffer.from(js).toString('base64')}`
}
globalThis.platformFixture={api:{get:async()=>({system_name:'Server name',language:'zh-CN',timezone:'Asia/Shanghai'})},locale:'zh-CN'}
const storeSource=readFileSync(new URL('../src/store/platformConfig.ts',import.meta.url),'utf8')
  .replace("'pinia'",JSON.stringify(import.meta.resolve('pinia'))).replace("'vue'",JSON.stringify(import.meta.resolve('vue')))
  .replace(/import \{ platformConfigApi, type PlatformConfig \} from[^\n]+/,'const platformConfigApi={get:()=>globalThis.platformFixture.api.get()}')
  .replace(/import \{ setLocale \} from[^\n]+/,'const setLocale=value=>{globalThis.platformFixture.locale=value}')
const storeUrl=moduleUrl(storeSource)
const {usePlatformConfigStore}=await import(storeUrl)
const timeSource=readFileSync(new URL('../src/utils/platformTime.ts',import.meta.url),'utf8').replace("'../store/platformConfig'",JSON.stringify(storeUrl))
const {parsePlatformTimestamp,formatPlatformDateTime,formatPlatformTime}=await import(moduleUrl(timeSource))

test('committed platform configuration defeats a delayed startup read and supports forced reload',async()=>{
  setActivePinia(createPinia());const store=usePlatformConfigStore();let finish
  globalThis.platformFixture.api.get=()=>new Promise(resolve=>{finish=resolve})
  const oldRead=store.load();assert.equal(store.loading,true)
  store.applySaved({system_name:'Committed name',language:'en',timezone:'UTC'})
  finish({system_name:'Old name',language:'zh-CN',timezone:'Asia/Shanghai'});await oldRead
  assert.equal(store.system_name,'Committed name');assert.equal(store.language,'en');assert.equal(store.timezone,'UTC');assert.equal(store.loading,false)
  globalThis.platformFixture.api.get=async()=>({system_name:'Fresh name',language:'zh-CN',timezone:'Asia/Shanghai'})
  await store.load(true);assert.equal(store.system_name,'Fresh name');assert.equal(globalThis.platformFixture.locale,'zh-CN')
})

test('naive backend timestamps are UTC and the saved timezone affects the same instant',()=>{
  setActivePinia(createPinia());const store=usePlatformConfigStore()
  assert.equal(parsePlatformTimestamp('2026-10-11T12:34:56.123456').toISOString(),'2026-10-11T12:34:56.123Z')
  assert.equal(parsePlatformTimestamp('2026-10-11 20:34:56+08:00').toISOString(),'2026-10-11T12:34:56.000Z')
  store.applySaved({language:'en',timezone:'UTC'});const utc=formatPlatformDateTime('2026-10-11T12:34:56')
  store.applySaved({timezone:'Asia/Shanghai'});const shanghai=formatPlatformDateTime('2026-10-11T12:34:56Z')
  assert.match(utc,/12:34:56/);assert.match(utc,/UTC/);assert.match(shanghai,/20:34:56/)
  assert.equal(formatPlatformDateTime(undefined),'—');assert.equal(formatPlatformDateTime('not-a-date'),'not-a-date')
  assert.match(formatPlatformTime('2026-10-11T12:34:56'), /20:34:56/)
  store.applySaved({timezone:'UTC'})
  assert.match(formatPlatformTime('2026-10-11T12:34:56'), /12:34:56/)
})

test('actual basic-config form keeps unsaved and rejected preferences local and applies only the saved request',async()=>{
  setActivePinia(createPinia());const platform=usePlatformConfigStore();let rejectSave=true,complete,submitted
  globalThis.basicConfigFixture={platform,api:{
    getAll:async()=>({groups:{basic:[{key:'system_name',value:'Initial name'},{key:'language',value:'zh-CN'},{key:'timezone',value:'Asia/Shanghai'}]}}),
    getAiModels:async()=>({models:[],scenes:[]}),
    save:async(group,items)=>{submitted={group,items};if(rejectSave)throw new Error('Rejected');return await new Promise(resolve=>{complete=resolve})},
  }}
  globalThis.document={querySelector:()=>null,getElementById:()=>null}
  let source=readFileSync(new URL('../src/views/settings/SystemConfigView.vue',import.meta.url),'utf8').replace('</script>','defineExpose({editingValues,handleSave,handleReset})\n</script>')
  source=compileScript(parse(source).descriptor,{id:'basic-config-regression'}).content.replace(/import[\s\S]*? from ['"]([^'"]+)['"];?/g,(full,location)=>{
    if(location==='vue')return full.replace("'vue'",JSON.stringify(import.meta.resolve('vue')))
    if(location==='ant-design-vue')return 'const AInput={},AInputPassword={},AInputNumber={},ASelect={},ADrawer={},AModal={},ASlider={},ACheckboxGroup={},AAlert={},ACard={},AButton={},ASpin={}'
    if(location==='@ant-design/icons-vue')return 'const HistoryOutlined={}'
    if(location.includes('api/systemConfig'))return 'const systemConfigApi=globalThis.basicConfigFixture.api'
    if(location.includes('store/auth'))return "const useAuthStore=()=>({user:{id:'editor',role:'editor'},hasPermission:permission=>permission==='admin:users'})"
    if(location.includes('api/client'))return 'const get=async()=>[]'
    if(location.includes('useToast'))return 'const useToast=()=>({success(){},error(){}})'
    if(location.includes('useLanguage'))return 'const useLanguage=()=>({t:key=>key})'
    if(location.includes('store/platformConfig'))return 'const usePlatformConfigStore=()=>globalThis.basicConfigFixture.platform'
    if(location.includes('utils/platformTime'))return 'const formatPlatformDateTime=value=>value'
    return ''
  })
  const component=(await import(moduleUrl(source))).default;component.render=()=>null
  const renderer=createRenderer({patchProp(){},insert(){},remove(){},createElement(){return {}},createText(){return {}},createComment(){return {}},setText(){},setElementText(){},parentNode(){return null},nextSibling(){return null}})
  const app=renderer.createApp(component);const editor=app.mount({})
  try{
    await nextTick();await new Promise(resolve=>setTimeout(resolve,0))
    editor.editingValues.language='en';editor.editingValues.timezone='UTC';editor.editingValues.system_name='Saved name'
    await nextTick();assert.equal(platform.language,'zh-CN');assert.equal(platform.timezone,'Asia/Shanghai')
    await editor.handleSave('basic');assert.equal(platform.language,'zh-CN','rejected save cannot apply preferences')
    rejectSave=false;const saving=editor.handleSave('basic')
    editor.editingValues.language='zh-CN';editor.editingValues.timezone='Asia/Shanghai';editor.editingValues.system_name='Later unsaved name'
    complete({message:'saved'});await saving
    assert.equal(submitted.items.find(item=>item.key==='language').value,'en')
    assert.equal(platform.language,'en');assert.equal(platform.timezone,'UTC');assert.equal(platform.system_name,'Saved name')
    assert.equal(editor.editingValues.system_name,'Later unsaved name')
    editor.handleReset('basic');assert.equal(editor.editingValues.system_name,'Saved name')
  }finally{app.unmount();delete globalThis.basicConfigFixture;delete globalThis.document}
})
