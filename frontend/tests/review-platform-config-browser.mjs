// CORE-017: actual UI saves, anonymous reload, timezone readback, draft isolation.
import { pathToFileURL } from 'node:url'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE||''))
const origin=process.env.REVIEW_FRONTEND_ORIGIN||'http://127.0.0.1:5179'
const evidence=path.resolve('../docs/review/evidence/platform-config-browser')
await mkdir(evidence,{recursive:true})
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE})
const context=await browser.newContext({viewport:{width:1440,height:1000}})
const page=await context.newPage()
const checks=[],errors=[],network=[]
let original,changed=false,restored=false,observedTask
page.on('pageerror',error=>errors.push(error.message))
page.on('response',async response=>{
  const request=response.request(),url=new URL(response.url())
  if(!url.pathname.endsWith('/auth/platform-config')&&!(request.method()==='PUT'&&url.pathname.endsWith('/system-config')))return
  let input;try{input=request.postDataJSON()}catch{ /* GET has no request body. */ };if(input?.group&&input.group!=='basic')return
  network.push({method:request.method(),url:response.url(),status:response.status(),input,body:await response.json().catch(()=>null)})
})
function check(name,values={}){checks.push({name,status:'passed',...values});console.log(name)}
async function fieldsReady(){await page.locator('#config-group-basic [data-config-key="system_name"] input').waitFor()}
async function selectBasic(key,value){
  const labels={en:'English','zh-CN':'简体中文','Asia/Shanghai':'Asia/Shanghai',UTC:'UTC'}
  await page.locator(`#config-group-basic [data-config-key="${key}"] .ant-select-selector`).click()
  await page.locator(`.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[title="${labels[value]}"]`).click()
}
async function saveBasic(values){
  await page.goto(origin+'/ops/config');await fieldsReady()
  await page.locator('#config-group-basic [data-config-key="system_name"] input').fill(values.system_name)
  await selectBasic('language',values.language);await selectBasic('timezone',values.timezone)
  const response=await Promise.all([page.waitForResponse(response=>response.request().method()==='PUT'&&new URL(response.url()).pathname.endsWith('/system-config')),page.locator('#config-group-basic .config-card-footer__right button.ant-btn-primary').click()])
  assert.equal(response[0].status(),200)
  await page.waitForFunction(language=>document.documentElement.lang===language,values.language)
  await page.waitForFunction(name=>document.querySelector('.sidebar__logo-text')?.textContent.trim()===name,values.system_name)
}
async function openTasks(){
  const code=process.env.REVIEW_ONTOLOGY_CODE||'review_browser_final'
  await page.goto(origin+'/ontology/list/'+code)
  await page.locator('.ontology-detail__title').waitFor()
  await page.locator('.attr-panel__loading').waitFor({state:'hidden'})
  await page.getByRole('button',{name:'📝 任务记录'}).click()
  await page.locator('.resource-card').first().waitFor()
}
try{
  await page.goto(origin+'/login')
  const config=await page.request.get(origin+'/api/v1/auth/platform-config');assert.equal(config.status(),200);original=await config.json()
  await page.locator('#login-username').fill('admin');await page.locator('#login-password').fill(process.env.REVIEW_PASSWORD||'')
  await page.locator('.login__form button[type=submit]').click();await page.locator('.topbar__user-name').waitFor()
  const name='平台配置UI验收 '+Date.now().toString(36)
  changed=true;await saveBasic({system_name:name,language:'en',timezone:'UTC'})
  assert.equal(await page.locator('html').getAttribute('lang'),'en')
  assert.equal(await page.getByRole('link',{name:'Connections',exact:true}).isVisible(),true)
  assert.match(await page.title(),/System Config/);assert.match(await page.title(),new RegExp(name))
  check('saved branding, shell navigation, document title and locale apply',{system_name:name,language:'en',timezone:'UTC'})
  await page.screenshot({path:path.join(evidence,'01-saved-en-utc.png'),fullPage:true,animations:'disabled'})
  await page.goto(origin+'/skills');await page.locator('.ant-pagination-prev').waitFor();assert.equal(await page.locator('.ant-pagination-prev').getAttribute('title'),'Previous Page');check('actual Ant Design pagination uses English locale')
  await page.goto(origin+'/ops/config');await fieldsReady()
  await page.reload();await fieldsReady();assert.equal(await page.locator('.sidebar__logo-text').innerText(),name);assert.equal(await page.locator('html').getAttribute('lang'),'en')
  check('reload restores the saved server configuration')
  await selectBasic('language','zh-CN')
  assert.equal(await page.locator('html').getAttribute('lang'),'en')
  await page.goto(origin+'/ontology/list');await page.getByRole('link',{name:'Connections',exact:true}).waitFor()
  assert.equal(await page.locator('html').getAttribute('lang'),'en')
  check('unsaved language draft does not leak on edit or leave')
  const anonymous=await browser.newContext();const login=await anonymous.newPage();login.on('pageerror',error=>errors.push(error.message))
  await login.goto(origin+'/login');await login.waitForFunction(name=>document.querySelector('.login__brand')?.textContent.trim()===name,name)
  assert.equal(await login.locator('html').getAttribute('lang'),'en');assert.equal(await login.locator('#login-username').getAttribute('placeholder'),'Enter your username')
  assert.equal(await login.getByRole('button',{name:'Sign in',exact:true}).isVisible(),true)
  assert.match(await login.title(),/Sign In/)
  await login.screenshot({path:path.join(evidence,'02-anonymous-brand-en.png'),fullPage:true,animations:'disabled'})
  await anonymous.close();check('fresh anonymous context loads safe saved branding and language')
  const code=process.env.REVIEW_ONTOLOGY_CODE||'review_browser_final'
  await page.goto(origin+'/ontology/list/'+code)
  const [taskResponse]=await Promise.all([page.waitForResponse(response=>new URL(response.url()).pathname.endsWith('/tasks')),page.getByRole('button',{name:'📝 任务记录'}).click()])
  const tasks=await taskResponse.json();assert.ok(tasks.length>0,'timezone check requires real persisted task records')
  await page.locator('.resource-card').first().waitFor()
  observedTask=tasks[0]
  const timestamp=tasks[0].created_at,instant=new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(timestamp)?timestamp:timestamp+'Z')
  const expected=new Intl.DateTimeFormat('en',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false,timeZone:'UTC',timeZoneName:'short'}).format(instant)
  assert.ok((await page.locator('.resource-card').first().innerText()).includes(expected))
  check('actual persisted task UTC instant renders in saved UTC timezone',{record_id:tasks[0].id,raw_timestamp:timestamp,displayed:expected})
  await page.screenshot({path:path.join(evidence,'03-real-task-utc.png'),fullPage:true,animations:'disabled'})
}catch(error){errors.push(error.message);throw error}
finally{
  if(changed&&original){
    try{await saveBasic(original);restored=true;check('original configuration restored through UI',original);if(observedTask){await openTasks();const timestamp=observedTask.created_at;const instant=new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(timestamp)?timestamp:timestamp+'Z');const expected=new Intl.DateTimeFormat(original.language,{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false,timeZone:original.timezone,timeZoneName:'short'}).format(instant);assert.ok((await page.locator('.resource-card').filter({hasText:observedTask.id}).innerText()).includes(expected));check('same task instant returns to the restored server timezone',{record_id:observedTask.id,displayed:expected});await page.screenshot({path:path.join(evidence,'04-restored-task-timezone.png'),fullPage:true,animations:'disabled'})}}
    catch(error){errors.push('UI restore verification failed: '+error.message);await page.screenshot({path:path.join(evidence,'restore-verification-error.png'),fullPage:true,animations:'disabled'});await writeFile(path.join(evidence,'restore-verification-error.txt'),await page.locator('body').innerText())}
  }
  await writeFile(path.join(evidence,'result.json'),JSON.stringify({checks,errors,restored,original,network},null,2))
  await browser.close()
  if(!restored||errors.length)process.exitCode=1
}
