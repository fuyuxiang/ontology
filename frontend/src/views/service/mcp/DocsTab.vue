<template>
  <div class="docs">
    <section class="docs__quickstart">
      <h2>快速接入</h2>
      <div class="steps">
        <div v-for="(text, i) in steps" :key="i" class="step">
          <span class="step__num">{{ i + 1 }}</span>
          <span class="step__text">{{ text }}</span>
        </div>
      </div>

      <div class="code-tabs">
        <button
          v-for="c in clients"
          :key="c.key"
          :class="{ active: activeClient === c.key }"
          :aria-pressed="activeClient === c.key"
          @click="activeClient = c.key"
        >{{ c.label }}</button>
      </div>
      <pre class="code-block"><code>{{ clientConfigs[activeClient] }}</code><button class="copy-btn" @click="copyConfig">{{ copied ? '已复制' : '复制' }}</button></pre>
    </section>

    <p class="docs__auth">Bearer 使用登录获得的访问令牌；令牌过期后需重新登录或刷新。配置的 MCP API Key 使用 <code>X-API-Key: YOUR_MCP_API_KEY</code>，其权限仅限只读。连接后先调用 initialize，再调用 tools/list；写入工具需要有执行权限的用户访问令牌。</p>
    <section class="docs__tools">
      <h2>工具清单</h2>
      <a-alert v-if="loadError" type="error" show-icon message="工具清单加载失败" :description="loadError" style="margin-bottom:16px">
        <template #action><a-button size="small" @click="loadTools">重试</a-button></template>
      </a-alert>
      <a-spin :spinning="loading" tip="正在加载工具…"><div class="tool-grid">
        <button type="button"
          v-for="tool in tools"
          :key="tool.name"
          class="tool-card"
          @click="selectedTool = tool"
        >
          <div class="tool-card__header">
            <span class="tool-card__name">{{ tool.name }}</span>
            <span class="tool-card__tag">{{ getCategory(tool.name) }}</span>
          </div>
          <p class="tool-card__desc">{{ tool.description }}</p>
          <div class="tool-card__params">
            {{ Object.keys(tool.inputSchema.properties || {}).length }} 个参数
          </div>
        </button>
      </div><a-empty v-if="!loading && !loadError && !tools.length" description="暂无可用工具" /></a-spin>
    </section>

    <ToolDrawer
      v-if="selectedTool"
      :tool="selectedTool"
      @close="selectedTool = null"
    />
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Alert as AAlert, Button as AButton, Empty as AEmpty, Spin as ASpin, message } from 'ant-design-vue'
import { getMcpTools, type McpToolSchema } from '../../../api/mcp'
import ToolDrawer from './ToolDrawer.vue'
import { copyText } from '../../../utils/markdownExport'

const tools = ref<McpToolSchema[]>([])
const loading = ref(false)
const loadError = ref('')
const copied = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | undefined
const selectedTool = ref<McpToolSchema | null>(null)
const activeClient = ref<'claude' | 'cursor' | 'curl'>('claude')

const steps = ['获取登录访问令牌或 MCP API Key', '配置 MCP 端点', '初始化并发现工具']
const clients = [
  { key: 'claude', label: 'Claude Desktop' },
  { key: 'cursor', label: 'Cursor' },
  { key: 'curl', label: 'curl / Python' },
] as const

const origin = window.location.origin
const endpoint = `${new URL(import.meta.env.VITE_API_BASE_URL || '/api/v1', origin).toString().replace(/\/$/, '')}/mcp`
const clientConfigs: Record<'claude' | 'cursor' | 'curl', string> = {
  claude: `{
  "mcpServers": {
    "ontology": {
      "url": "${endpoint}",
      "headers": {
        "Authorization": "Bearer YOUR_ACCESS_TOKEN"
      }
    }
  }
}`,
  cursor: `{
  "mcp": {
    "servers": {
      "ontology": {
        "type": "streamable-http",
        "url": "${endpoint}",
        "headers": {
          "Authorization": "Bearer YOUR_ACCESS_TOKEN"
        }
      }
    }
  }
}`,
  curl: `curl -X POST ${endpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"review-client","version":"1.0"}}
  }'

curl -X POST ${endpoint} -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ACCESS_TOKEN" -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' `,
}

function getCategory(name: string): string {
  if (name.includes('query') || name.includes('sql') || name.includes('find')) return '数据查询'
  if (name.includes('attr') || name.includes('capabilities')) return '元数据'
  if (name.includes('python') || name.includes('file')) return 'Python 运行时'
  return '其他'
}

async function copyConfig() {
  if (await copyText(clientConfigs[activeClient.value])) {
    copied.value = true
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = false }, 1500)
  } else message.error('复制失败，请手动选择并复制配置')
}

async function loadTools() {
  if (loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    const res = await getMcpTools()
    tools.value = res.tools || []
  } catch (e: any) { loadError.value = e.response?.data?.detail || e.message || '无法读取工具，请重试' }
  finally { loading.value = false }
}

onMounted(loadTools)
onBeforeUnmount(() => clearTimeout(copyTimer))
</script>

<style scoped>
.docs { padding: 0; }
.docs__quickstart { background: var(--neutral-50, #f8f9fa); border: 1px solid var(--neutral-100, #f1f3f5); border-radius: var(--radius-lg, 12px); padding: 24px; margin-bottom: 24px; }
.docs__quickstart h2 { font-size: 15px; font-weight: 600; margin: 0 0 16px; color: var(--neutral-900, #212529); }
.steps { display: flex; flex-wrap: wrap; gap: 24px; margin-bottom: 20px; }
.step { display: flex; align-items: center; gap: 10px; }
.step__num { width: 26px; height: 26px; border-radius: 50%; background: var(--primary, #2563eb); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.step__text { font-size: 13px; color: var(--neutral-700, #333); }
.code-tabs { display: flex; gap: 4px; margin-bottom: 12px; }
.code-tabs button { font-size: 11px; padding: 4px 10px; border: 1px solid var(--neutral-200, #e5e5e5); border-radius: 6px; background: var(--neutral-0, #fff); cursor: pointer; color: var(--neutral-600, #555); transition: all 0.15s; }
.code-tabs button:hover { border-color: var(--primary, #2563eb); color: var(--primary, #2563eb); }
.code-tabs button.active { background: var(--primary, #2563eb); color: #fff; border-color: var(--primary, #2563eb); }
.code-block { background: var(--neutral-950, #0f1117); color: #a6e3a1; padding: 16px; border-radius: var(--radius-md, 8px); font-size: 12px; overflow-x: auto; position: relative; white-space: pre; font-family: var(--font-mono, monospace); }
.code-block .copy-btn { position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.1); border: none; color: #cdd6f4; padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer; }

.docs__tools h2 { font-size: 15px; font-weight: 600; margin: 0 0 16px; color: var(--neutral-900, #212529); }
.tool-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.tool-card { background: var(--neutral-0, #fff); border: 1px solid var(--neutral-100, #f1f3f5); border-radius: var(--radius-lg, 12px); padding: 20px; cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s; font: inherit; text-align: left; min-width: 0; overflow-wrap: anywhere; }
.tool-card:hover { border-color: var(--primary, #2563eb); box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08); }
.tool-card__header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 8px; }
.tool-card__name { font-size: 13px; font-weight: 600; color: var(--neutral-900, #111); }
.tool-card__tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; background: #eff6ff; color: var(--primary, #2563eb); font-weight: 500; }
.tool-card__desc { font-size: 13px; color: var(--neutral-600, #4b5563); margin: 0 0 8px; line-height: 1.6; }
.tool-card__params { font-size: 12px; color: var(--neutral-500, #6b7280); }
.tool-card__tag { flex-shrink: 0; }
.tool-card:focus-visible, .code-tabs button:focus-visible, .copy-btn:focus-visible { outline: 2px solid var(--primary, #2563eb); outline-offset: 3px; }
.code-tabs { flex-wrap: wrap; }
</style>
