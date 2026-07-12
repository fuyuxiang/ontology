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
          @click="activeClient = c.key"
        >{{ c.label }}</button>
      </div>
      <pre class="code-block"><code>{{ clientConfigs[activeClient] }}</code><button class="copy-btn" @click="copyConfig">复制</button></pre>
    </section>

    <section class="docs__tools">
      <h2>工具清单</h2>
      <div class="tool-grid">
        <div
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
        </div>
      </div>
    </section>

    <ToolDrawer
      v-if="selectedTool"
      :tool="selectedTool"
      @close="selectedTool = null"
    />
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMcpTools, type McpToolSchema } from '../../../api/mcp'
import ToolDrawer from './ToolDrawer.vue'

const tools = ref<McpToolSchema[]>([])
const selectedTool = ref<McpToolSchema | null>(null)
const activeClient = ref<'claude' | 'cursor' | 'curl'>('claude')

const steps = ['获取认证密钥', '配置 MCP 端点', '开始调用']
const clients = [
  { key: 'claude', label: 'Claude Desktop' },
  { key: 'cursor', label: 'Cursor' },
  { key: 'curl', label: 'curl / Python' },
] as const

const origin = window.location.origin
const clientConfigs: Record<'claude' | 'cursor' | 'curl', string> = {
  claude: `{
  "mcpServers": {
    "ontology": {
      "url": "${origin}/api/v1/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}`,
  cursor: `{
  "mcp": {
    "servers": {
      "ontology": {
        "type": "streamable-http",
        "url": "${origin}/api/v1/mcp",
        "headers": {
          "Authorization": "Bearer YOUR_API_KEY"
        }
      }
    }
  }
}`,
  curl: `curl -X POST ${origin}/api/v1/mcp \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'`,
}

function getCategory(name: string): string {
  if (name.includes('query') || name.includes('sql') || name.includes('find')) return '数据查询'
  if (name.includes('attr') || name.includes('capabilities')) return '元数据'
  if (name.includes('python') || name.includes('file')) return 'Python 运行时'
  return '其他'
}

async function copyConfig() {
  try {
    await navigator.clipboard.writeText(clientConfigs[activeClient.value])
  } catch { /* ignore */ }
}

async function loadTools() {
  try {
    const res = await getMcpTools()
    tools.value = res.tools || []
  } catch { /* ignore */ }
}

onMounted(loadTools)
</script>

<style scoped>
.docs { padding: 0; }
.docs__quickstart { background: var(--neutral-50, #f8f9fa); border: 1px solid var(--neutral-100, #f1f3f5); border-radius: var(--radius-lg, 12px); padding: 24px; margin-bottom: 24px; }
.docs__quickstart h2 { font-size: 15px; font-weight: 600; margin: 0 0 16px; color: var(--neutral-900, #212529); }
.steps { display: flex; gap: 24px; margin-bottom: 20px; }
.step { display: flex; align-items: center; gap: 10px; }
.step__num { width: 26px; height: 26px; border-radius: 50%; background: var(--semantic-600, #4c6ef5); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.step__text { font-size: 13px; color: var(--neutral-700, #495057); }
.code-tabs { display: flex; gap: 4px; margin-bottom: 12px; }
.code-tabs button { font-size: 11px; padding: 4px 10px; border: 1px solid var(--neutral-200, #e9ecef); border-radius: 6px; background: var(--neutral-0, #fff); cursor: pointer; color: var(--neutral-600, #868e96); transition: all 0.15s; }
.code-tabs button:hover { border-color: var(--semantic-600, #4c6ef5); color: var(--semantic-600, #4c6ef5); }
.code-tabs button.active { background: var(--semantic-600, #4c6ef5); color: #fff; border-color: var(--semantic-600, #4c6ef5); }
.code-block { background: var(--neutral-950, #0f1117); color: #a6e3a1; padding: 16px; border-radius: var(--radius-md, 8px); font-size: 12px; overflow-x: auto; position: relative; white-space: pre; font-family: var(--font-mono, monospace); }
.code-block .copy-btn { position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.1); border: none; color: #cdd6f4; padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer; }

.docs__tools h2 { font-size: 15px; font-weight: 600; margin: 0 0 16px; color: var(--neutral-900, #212529); }
.tool-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.tool-card { background: var(--neutral-0, #fff); border: 1px solid var(--neutral-100, #f1f3f5); border-radius: var(--radius-lg, 12px); padding: 20px; cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s; }
.tool-card:hover { border-color: var(--semantic-200, #bac8ff); box-shadow: 0 4px 16px rgba(76, 110, 245, 0.08); }
.tool-card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tool-card__name { font-size: 13px; font-weight: 600; color: var(--neutral-900, #212529); }
.tool-card__tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; background: var(--semantic-50, #eef2ff); color: var(--semantic-600, #4c6ef5); font-weight: 500; }
.tool-card__desc { font-size: 12px; color: var(--neutral-500, #adb5bd); margin: 0 0 8px; line-height: 1.5; }
.tool-card__params { font-size: 11px; color: var(--neutral-400, #ced4da); }
</style>
