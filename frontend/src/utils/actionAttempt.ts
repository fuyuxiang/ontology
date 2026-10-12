/** Store correlation only; business inputs and credentials remain on the server. */
export interface ActionAttempt { key:string; state:string; execution_id?:string }
function storageKey(owner:string, action:string) { if (!owner || !action) throw new Error('缺少当前账号或行动'); return `ontology-action-attempt:${owner}:${action}` }
export function readActionAttempt(owner:string, action:string):ActionAttempt | null {
  const raw=localStorage.getItem(storageKey(owner, action))
  if (!raw) return null
  const value=JSON.parse(raw)
  if (typeof value?.key !== 'string' || !value.key || typeof value?.state !== 'string' || !value.state) throw new Error('执行关联记录损坏，请先在操作任务中核对执行结果')
  return {key:value.key,state:value.state,execution_id:value.execution_id}
}
export function saveActionAttempt(owner:string, action:string, attempt:ActionAttempt) { localStorage.setItem(storageKey(owner,action),JSON.stringify({key:attempt.key,state:attempt.state,execution_id:attempt.execution_id})) }
export function ensureActionAttempt(owner:string, action:string):ActionAttempt {
  const existing=readActionAttempt(owner,action)
  if (existing) return existing
  const bytes=globalThis.crypto.getRandomValues(new Uint8Array(16))
  const attempt={key:`ui-${Array.from(bytes,byte=>byte.toString(16).padStart(2,'0')).join('')}`,state:'unresolved'}
  saveActionAttempt(owner,action,attempt)
  return attempt
}
export function clearCompletedActionAttempt(owner:string, action:string) {
  const existing=readActionAttempt(owner,action)
  if (existing && !['succeeded','failed'].includes(existing.state)) throw new Error('执行结果尚未确定，请核对已有执行结果后再开始新执行')
  localStorage.removeItem(storageKey(owner,action))
}
