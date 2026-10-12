// Real authenticated reloads with delayed/rejected /me transport, no business API mocking.
import {pathToFileURL} from 'node:url'
import {mkdir,writeFile} from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE||''))
const origin=process.env.REVIEW_FRONTEND_ORIGIN||'http://127.0.0.1:5179'
const code=process.env.REVIEW_ONTOLOGY_CODE||'review_browser_final'
const evidence=path.resolve('../docs/review/evidence/session-restore-browser')
await mkdir(evidence,{recursive:true})
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE})
const context=await browser.newContext({viewport:{width:1440,height:1000}})
const page=await context.newPage(),checks=[],errors=[],network=[]
let recoveryPending=false,earlyProtectedRequests=0,mode='delay'
page.on('pageerror',error=>errors.push(error.message))
page.on('request',request=>{const pathname=new URL(request.url()).pathname;if(recoveryPending&&/^\/api\/v1\/(?:scenarios|entities|assets|connections|ontology)\b/.test(pathname))earlyProtectedRequests++})
page.on('response',response=>{const pathname=new URL(response.url()).pathname;if(pathname.startsWith('/api/'))network.push({method:response.request().method(),path:pathname,status:response.status()})})
function check(name,extra={}){checks.push({name,status:'passed',...extra});console.log(name)}
async function tasks(){
 await page.getByRole('button',{name:'📝 任务记录'}).click()
 await page.getByRole('heading',{name:'操作任务记录',exact:true}).waitFor()
 await page.locator('.resource-card').first().waitFor()
 assert.equal(await page.getByRole('button',{name:'📝 任务记录'}).getAttribute('aria-pressed'),'true')
}
try{
 await page.goto(origin+'/login');await page.locator('#login-username').fill('admin');await page.locator('#login-password').fill(process.env.REVIEW_PASSWORD||'');await page.locator('.login__form button[type=submit]').click();await page.locator('.topbar__user-name').waitFor()
 await page.route('**/api/v1/auth/me',async route=>{
  recoveryPending=true
  if(mode==='503'){mode='delay';await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"isolated transport failure"}'});recoveryPending=false;return}
  if(mode==='network'){mode='delay';await route.abort('failed');recoveryPending=false;return}
  const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,350));recoveryPending=false;await route.fulfill({response})
 })
 for(let attempt=1;attempt<=5;attempt++){
  await page.goto(origin+'/ontology/list/'+code);await tasks()
  assert.equal(earlyProtectedRequests,0,'protected pages must wait until /me completes')
  check('delayed real session reload '+attempt+' keeps selected task tab',{record_id:(await page.locator('.resource-card').first().innerText()).match(/ID：([^\s]+)/)?.[1]})
 }
 for(const failure of ['503','network']){
  mode=failure;await page.goto(origin+'/ontology/list/'+code)
  await page.getByRole('alert').filter({hasText:'会话恢复失败'}).waitFor()
  assert.equal(await page.getByRole('status').filter({hasText:'正在恢复会话'}).count(),0)
  assert.equal(await page.getByRole('button',{name:'📝 任务记录'}).count(),0,'failed restore must not mount a protected page')
  await page.getByRole('button',{name:'重试',exact:true}).click();await tasks();assert.equal(earlyProtectedRequests,0)
  check(failure+' restore failure ends loading and explicit retry restores real tasks')
 }
 await page.screenshot({path:path.join(evidence,'restored-task-tab.png'),fullPage:true,animations:'disabled'})
}catch(error){errors.push(error.message);await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true,animations:'disabled'});throw error}
finally{await writeFile(path.join(evidence,'result.json'),JSON.stringify({checks,errors,earlyProtectedRequests,network},null,2));await browser.close();if(errors.length)process.exitCode=1}
