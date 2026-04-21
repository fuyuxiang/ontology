<template>
  <div class="api-portal">
    <!-- 顶栏 -->
    <div class="portal-header">
      <div class="portal-header__left">
        <div class="portal-header__icon">
          <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
            <path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <div>
          <div class="portal-header__title">API 开放平台</div>
          <div class="portal-header__sub">已发布的智能体可通过 REST API 对外提供服务</div>
        </div>
      </div>
      <div class="portal-header__stats">
        <div class="stat-chip">
          <span class="stat-chip__num">{{ publishedAgents.length }}</span>
          <span class="stat-chip__label">已发布智能体</span>
        </div>
        <div class="stat-chip">
          <span class="stat-chip__num">{{ totalCalls }}</span>
          <span class="stat-chip__label">今日调用</span>
        </div>
      </div>
    </div>

    <!-- 主体 -->
    <div class="portal-body">
      <!-- 左侧智能体列表 -->
      <div class="portal-sidebar">
        <div class="sidebar-search">
          <a-input v-model:value="search" placeholder="搜索智能体..." allow-clear>
            <template #prefix>
              <SearchOutlined style="color: #aaa" />
            </template>
          </a-input>
        </div>
        <div class="agent-list">
          <div
            v-for="a in filteredAgents"
            :key="a.id"
            class="agent-item"
            :class="{ active: selected?.id === a.id }"
            @click="selectAgent(a)"
          >
            <div class="agent-item__avatar" :style="{ background: agentColor(a.id) }">
              {{ a.name.charAt(0) }}
            </div>
            <div class="agent-item__info">
              <div class="agent-item__name">{{ a.name }}</div>
              <div class="agent-item__desc">{{ a.description || '暂无描述' }}</div>
            </div>
            <a-tag color="success" size="small">已发布</a-tag>
          </div>
          <a-empty v-if="filteredAgents.length === 0" description="暂无已发布智能体" style="margin-top: 40px" />
        </div>
      </div>

      <!-- 右侧详情 -->
      <div class="portal-detail" v-if="selected && apiInfo">
        <!-- 智能体信息头 -->
        <div class="detail-hero">
          <div class="detail-hero__avatar" :style="{ background: agentColor(selected.id) }">
            {{ selected.name.charAt(0) }}
          </div>
          <div class="detail-hero__info">
            <div class="detail-hero__name">{{ selected.name }}</div>
            <div class="detail-hero__desc">{{ selected.description || '暂无描述' }}</div>
            <div class="detail-hero__tags">
              <a-tag v-for="t in (selected.tags || [])" :key="t" size="small">{{ t }}</a-tag>
              <a-tag color="blue" size="small" v-if="selected.model_name">{{ selected.model_name }}</a-tag>
            </div>
          </div>
          <div class="detail-hero__actions">
            <a-button size="small" @click="tryVisible = true">
              <template #icon><ThunderboltOutlined /></template>
              在线调试
            </a-button>
          </div>
        </div>

        <a-tabs v-model:activeKey="detailTab" class="detail-tabs">
          <!-- 接入信息 -->
          <a-tab-pane key="info" tab="接入信息">
            <div class="info-section">
              <div class="info-block">
                <div class="info-block__label">接口地址</div>
                <div class="info-block__value">
                  <code class="endpoint-code">POST {{ fullEndpoint }}</code>
                  <a-button size="small" type="text" @click="copy(fullEndpoint)">
                    <template #icon><CopyOutlined /></template>
                  </a-button>
                </div>
              </div>
              <div class="info-block">
                <div class="info-block__label">API Key</div>
                <div class="info-block__value">
                  <code class="key-code">{{ showKey ? apiInfo.api_key : maskKey(apiInfo.api_key) }}</code>
                  <a-button size="small" type="text" @click="showKey = !showKey">
                    <template #icon><EyeOutlined v-if="!showKey" /><EyeInvisibleOutlined v-else /></template>
                  </a-button>
                  <a-button size="small" type="text" @click="copy(apiInfo.api_key)">
                    <template #icon><CopyOutlined /></template>
                  </a-button>
                </div>
              </div>
              <div class="info-block">
                <div class="info-block__label">鉴权方式</div>
                <div class="info-block__value">
                  <span class="auth-badge">Header: <code>X-Agent-Key: &lt;API Key&gt;</code></span>
                </div>
              </div>
            </div>

            <!-- 请求/响应说明 -->
            <div class="schema-section">
              <div class="schema-title">请求体 (JSON)</div>
              <pre class="code-block">{{ requestSchema }}</pre>
              <div class="schema-title" style="margin-top: 16px">响应 (SSE 流式)</div>
              <pre class="code-block">{{ responseSchema }}</pre>
            </div>
          </a-tab-pane>

          <!-- 代码示例 -->
          <a-tab-pane key="code" tab="代码示例">
            <div class="code-lang-tabs">
              <a-segmented v-model:value="codeLang" :options="langOptions" size="small" />
            </div>
            <pre class="code-block code-block--large">{{ codeExample }}</pre>
            <a-button size="small" @click="copy(codeExample)" style="margin-top: 8px">
              <template #icon><CopyOutlined /></template>
              复制代码
            </a-button>
          </a-tab-pane>

          <!-- 调用日志（模拟） -->
          <a-tab-pane key="logs" tab="调用日志">
            <a-table
              :columns="logColumns"
              :data-source="mockLogs"
              size="small"
              :pagination="{ pageSize: 10 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="record.status === 200 ? 'success' : 'error'">{{ record.status }}</a-tag>
                </template>
                <template v-if="column.key === 'latency'">
                  {{ record.latency }}ms
                </template>
              </template>
            </a-table>
          </a-tab-pane>
        </a-tabs>
      </div>

      <!-- 未选中 -->
      <div class="portal-empty" v-else>
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 16 16" fill="none">
            <path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="#cbd5e1" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M9 3L7 13" stroke="#cbd5e1" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="empty-text">从左侧选择一个已发布的智能体</div>
        <div class="empty-sub">查看接入信息和代码示例</div>
      </div>
    </div>

    <!-- 在线调试抽屉 -->
    <a-drawer
      v-model:open="tryVisible"
      title="在线调试"
      width="480"
      :body-style="{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }"
    >
      <div class="try-messages" ref="tryMsgRef">
        <div v-if="tryMessages.length === 0" class="try-empty">
          <p>发送消息开始调试</p>
        </div>
        <div v-for="(m, i) in tryMessages" :key="i" class="try-msg" :class="m.role">
          <div class="try-msg__bubble">{{ m.content }}</div>
        </div>
      </div>
      <div class="try-input">
        <a-input
          v-model:value="tryInput"
          placeholder="输入消息..."
          @pressEnter="sendTry"
          :disabled="tryLoading"
        />
        <a-button type="primary" :loading="tryLoading" @click="sendTry" style="margin-left: 8px">发送</a-button>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import {
  SearchOutlined, CopyOutlined, EyeOutlined, EyeInvisibleOutlined, ThunderboltOutlined
} from '@ant-design/icons-vue'
import { agentsApi, type AgentItem, type ApiInfo } from '../../api/agents'

const agents = ref<AgentItem[]>([])
const search = ref('')
const selected = ref<AgentItem | null>(null)
const apiInfo = ref<ApiInfo | null>(null)
const detailTab = ref('info')
const showKey = ref(false)
const codeLang = ref('curl')
const tryVisible = ref(false)
const tryMessages = ref<{ role: string; content: string }[]>([])
const tryInput = ref('')
const tryLoading = ref(false)
const tryMsgRef = ref<HTMLElement | null>(null)

const totalCalls = ref(Math.floor(Math.random() * 500 + 100))

const COLORS = ['#6366f1','#3b82f6','#10b981','#f59e0b','#ec4899','#8b5cf6','#0ea5e9','#14b8a6']
function agentColor(id: string) {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) & 0xffffffff
  return COLORS[Math.abs(h) % COLORS.length]
}

const publishedAgents = computed(() => agents.value.filter(a => a.status === 'published'))
const filteredAgents = computed(() => {
  const q = search.value.toLowerCase()
  return publishedAgents.value.filter(a =>
    a.name.toLowerCase().includes(q) || (a.description || '').toLowerCase().includes(q)
  )
})

const fullEndpoint = computed(() =>
  selected.value ? `${window.location.origin}/api/v1/open/agents/${selected.value.id}/chat` : ''
)

function maskKey(k: string) {
  if (!k) return ''
  return k.slice(0, 8) + '••••••••••••••••' + k.slice(-4)
}

async function copy(text: string) {
  await navigator.clipboard.writeText(text)
  message.success('已复制')
}

const requestSchema = `{
  "messages": [
    { "role": "user", "content": "你好" }
  ],
  "stream": true   // 可选，默认 true（SSE 流式）
}`

const responseSchema = `// SSE 流式响应，每行格式：
data: <文本片段>

data: [DONE]   // 结束标志`

const langOptions = ['curl', 'Python', 'JavaScript', 'Java']

const codeExample = computed(() => {
  const ep = fullEndpoint.value
  const key = apiInfo.value?.api_key || '<YOUR_API_KEY>'
  if (codeLang.value === 'curl') return `curl -X POST "${ep}" \\
  -H "Content-Type: application/json" \\
  -H "X-Agent-Key: ${key}" \\
  -d '{"messages": [{"role": "user", "content": "你好"}]}'`

  if (codeLang.value === 'Python') return `import requests

url = "${ep}"
headers = {
    "Content-Type": "application/json",
    "X-Agent-Key": "${key}"
}
payload = {"messages": [{"role": "user", "content": "你好"}]}

with requests.post(url, json=payload, headers=headers, stream=True) as r:
    for line in r.iter_lines():
        if line.startswith(b"data: "):
            chunk = line[6:].decode()
            if chunk != "[DONE]":
                print(chunk, end="", flush=True)`

  if (codeLang.value === 'JavaScript') return `const resp = await fetch("${ep}", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Agent-Key": "${key}"
  },
  body: JSON.stringify({ messages: [{ role: "user", content: "你好" }] })
})

const reader = resp.body.getReader()
const decoder = new TextDecoder()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  const text = decoder.decode(value)
  for (const line of text.split("\\n")) {
    if (line.startsWith("data: ") && line.slice(6) !== "[DONE]")
      process.stdout.write(line.slice(6))
  }
}`

  return `// Java (OkHttp)
OkHttpClient client = new OkHttpClient();
RequestBody body = RequestBody.create(
    "{\\"messages\\":[{\\"role\\":\\"user\\",\\"content\\":\\"你好\\"}]}",
    MediaType.get("application/json")
);
Request request = new Request.Builder()
    .url("${ep}")
    .addHeader("X-Agent-Key", "${key}")
    .post(body)
    .build();
try (Response response = client.newCall(request).execute()) {
    System.out.println(response.body().string());
}`
})

const logColumns = [
  { title: '时间', dataIndex: 'time', key: 'time', width: 160 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 80 },
  { title: '延迟', dataIndex: 'latency', key: 'latency', width: 80 },
  { title: '输入 Token', dataIndex: 'input_tokens', key: 'input_tokens', width: 100 },
  { title: '输出 Token', dataIndex: 'output_tokens', key: 'output_tokens', width: 100 },
  { title: '来源 IP', dataIndex: 'ip', key: 'ip' },
]
const mockLogs = computed(() => {
  if (!selected.value) return []
  return Array.from({ length: 12 }, (_, i) => {
    const d = new Date(Date.now() - i * 1000 * 60 * (i + 1))
    return {
      key: i,
      time: d.toLocaleString('zh-CN'),
      status: Math.random() > 0.1 ? 200 : 500,
      latency: Math.floor(Math.random() * 800 + 200),
      input_tokens: Math.floor(Math.random() * 200 + 20),
      output_tokens: Math.floor(Math.random() * 400 + 50),
      ip: `192.168.${Math.floor(Math.random()*10)}.${Math.floor(Math.random()*200+10)}`,
    }
  })
})

async function selectAgent(a: AgentItem) {
  selected.value = a
  apiInfo.value = null
  showKey.value = false
  detailTab.value = 'info'
  try {
    apiInfo.value = await agentsApi.apiInfo(a.id)
  } catch (e) {
    message.error('获取 API 信息失败')
  }
}

async function sendTry() {
  const text = tryInput.value.trim()
  if (!text || tryLoading.value || !selected.value || !apiInfo.value) return
  tryMessages.value.push({ role: 'user', content: text })
  tryInput.value = ''
  tryLoading.value = true
  const assistantMsg = { role: 'assistant', content: '' }
  tryMessages.value.push(assistantMsg)
  const idx = tryMessages.value.length - 1
  await nextTick()
  tryMsgRef.value?.scrollTo({ top: tryMsgRef.value.scrollHeight, behavior: 'smooth' })

  try {
    const resp = await fetch(`/api/v1/open/agents/${selected.value.id}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Agent-Key': apiInfo.value.api_key,
      },
      body: JSON.stringify({ messages: tryMessages.value.slice(0, -1) }),
    })
    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      for (const line of decoder.decode(value, { stream: true }).split('\n')) {
        if (!line.startsWith('data: ')) continue
        const d = line.slice(6).trim()
        if (d === '[DONE]') continue
        tryMessages.value[idx].content += d
        await nextTick()
        tryMsgRef.value?.scrollTo({ top: tryMsgRef.value.scrollHeight, behavior: 'smooth' })
      }
    }
  } catch (e: any) {
    tryMessages.value[idx].content = '[错误] ' + e.message
  } finally {
    tryLoading.value = false
  }
}

onMounted(async () => {
  try {
    agents.value = await agentsApi.list()
    if (publishedAgents.value.length > 0) selectAgent(publishedAgents.value[0])
  } catch (e) {}
})
</script>

<style scoped>
.api-portal {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  overflow: hidden;
}
.portal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 28px 16px; background: #fff; border-bottom: 1px solid #e8edf2; flex-shrink: 0;
}
.portal-header__left { display: flex; align-items: center; gap: 14px; }
.portal-header__icon {
  width: 44px; height: 44px; border-radius: 12px;
  background: linear-gradient(135deg, #2e5bff 0%, #60a5fa 100%);
  display: flex; align-items: center; justify-content: center; color: #fff;
}
.portal-header__title { font-size: 18px; font-weight: 700; color: #1e293b; }
.portal-header__sub { font-size: 13px; color: #94a3b8; margin-top: 2px; }
.portal-header__stats { display: flex; gap: 16px; }
.stat-chip {
  display: flex; flex-direction: column; align-items: center;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px 20px;
}
.stat-chip__num { font-size: 22px; font-weight: 700; color: #2e5bff; line-height: 1; }
.stat-chip__label { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.portal-body { flex: 1; display: flex; overflow: hidden; }
.portal-sidebar {
  width: 260px; min-width: 260px; background: #fff; border-right: 1px solid #e8edf2;
  display: flex; flex-direction: column; overflow: hidden;
}
.sidebar-search { padding: 12px; border-bottom: 1px solid #f1f5f9; }
.agent-list { flex: 1; overflow-y: auto; padding: 8px; }
.agent-item {
  display: flex; align-items: center; gap: 10px; padding: 10px;
  border-radius: 8px; cursor: pointer; transition: background 0.15s;
}
.agent-item:hover { background: #f8fafc; }
.agent-item.active { background: #eff6ff; }
.agent-item__avatar {
  width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 16px; font-weight: 700;
}
.agent-item__info { flex: 1; min-width: 0; }
.agent-item__name { font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.agent-item__desc { font-size: 11px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.portal-detail { flex: 1; overflow-y: auto; padding: 24px 28px; }
.portal-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.empty-text { font-size: 15px; font-weight: 600; color: #94a3b8; }
.empty-sub { font-size: 13px; color: #cbd5e1; margin-top: 4px; }
.detail-hero {
  display: flex; align-items: flex-start; gap: 16px;
  background: #fff; border: 1px solid #e8edf2; border-radius: 12px;
  padding: 20px 24px; margin-bottom: 20px;
}
.detail-hero__avatar {
  width: 52px; height: 52px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 22px; font-weight: 700;
}
.detail-hero__info { flex: 1; }
.detail-hero__name { font-size: 18px; font-weight: 700; color: #1e293b; }
.detail-hero__desc { font-size: 13px; color: #64748b; margin-top: 4px; }
.detail-hero__tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.detail-hero__actions { flex-shrink: 0; }
.detail-tabs { background: #fff; border: 1px solid #e8edf2; border-radius: 12px; padding: 0 20px 20px; }
.info-section { display: flex; flex-direction: column; gap: 16px; margin-bottom: 24px; }
.info-block { display: flex; flex-direction: column; gap: 6px; }
.info-block__label { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.info-block__value { display: flex; align-items: center; gap: 8px; }
.endpoint-code {
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 6px 12px; font-size: 13px; color: #2e5bff; font-family: monospace;
}
.key-code {
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 6px 12px; font-size: 13px; color: #475569; font-family: monospace; letter-spacing: 0.05em;
}
.auth-badge {
  background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px;
  padding: 5px 12px; font-size: 13px; color: #1d4ed8;
}
.auth-badge code { background: none; font-family: monospace; }
.schema-section { margin-top: 8px; }
.schema-title { font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
.code-block {
  background: #0f172a; color: #e2e8f0; border-radius: 8px;
  padding: 16px; font-size: 12px; font-family: monospace;
  line-height: 1.6; overflow-x: auto; margin: 0; white-space: pre;
}
.code-block--large { min-height: 200px; }
.code-lang-tabs { margin-bottom: 12px; }
.try-messages {
  overflow-y: auto; display: flex; flex-direction: column; gap: 12px;
  padding-bottom: 12px; height: calc(100vh - 220px);
}
.try-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: #94a3b8; }
.try-msg { display: flex; }
.try-msg.user { justify-content: flex-end; }
.try-msg.assistant { justify-content: flex-start; }
.try-msg__bubble {
  max-width: 80%; padding: 10px 14px; border-radius: 12px;
  font-size: 13px; line-height: 1.6; white-space: pre-wrap;
}
.try-msg.user .try-msg__bubble { background: #2e5bff; color: #fff; border-bottom-right-radius: 4px; }
.try-msg.assistant .try-msg__bubble { background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; }
.try-input { display: flex; padding-top: 12px; border-top: 1px solid #f1f5f9; flex-shrink: 0; }
</style>
