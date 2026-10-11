<template>
  <a-drawer :open="true" :title="tool.name" :width="560" @close="$emit('close')">
      <div class="drawer__body">
        <p class="drawer__desc">{{ tool.description }}</p>

        <h4>参数</h4>
        <table class="param-table">
          <thead><tr><th>参数名</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
          <tbody>
            <tr v-for="(schema, name) in tool.inputSchema.properties" :key="name">
              <td><code>{{ name }}</code></td>
              <td>{{ schema.type }}</td>
              <td>{{ tool.inputSchema.required?.includes(String(name)) ? '是' : '否' }}</td>
              <td>{{ schema.description || '-' }}</td>
            </tr>
          </tbody>
        </table>

        <h4>请求示例</h4>
        <pre class="code-block"><code>{{ requestExample }}</code></pre>

        <h4>响应示例</h4>
        <pre class="code-block"><code>{{ responseExample }}</code></pre>
      </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Drawer as ADrawer } from 'ant-design-vue'
import type { McpToolSchema } from '../../../api/mcp'

const props = defineProps<{ tool: McpToolSchema }>()
defineEmits(['close'])

const requestExample = computed(() => JSON.stringify({
  jsonrpc: '2.0',
  id: 1,
  method: 'tools/call',
  params: {
    name: props.tool.name,
    arguments: Object.fromEntries(
      Object.entries(props.tool.inputSchema.properties || {}).map(([k, v]: [string, any]) => [k, v.type === 'string' ? '...' : v.type === 'integer' ? 0 : v.type === 'array' ? [] : {}])
    )
  }
}, null, 2))

const responseExample = computed(() => JSON.stringify({
  jsonrpc: '2.0',
  id: 1,
  result: {
    content: [{ type: 'text', text: '{"items": [...], "total_count": 10}' }]
  }
}, null, 2))
</script>

<style scoped>
.drawer__body { overflow-wrap: anywhere; }
.drawer__desc { font-size: 13px; color: var(--neutral-600, #555); margin: 0 0 20px; line-height: 1.5; }
.drawer__body h4 { font-size: 13px; font-weight: 600; color: var(--neutral-800, #333); margin: 20px 0 10px; }
.param-table { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 12px; margin-bottom: 8px; border: 1px solid var(--neutral-100, #f0f0f0); border-radius: 8px; overflow: hidden; }
.param-table th { text-align: left; padding: 8px 10px; background: var(--neutral-50, #fafafa); border-bottom: 1px solid var(--neutral-200, #e5e5e5); color: var(--neutral-600, #555); font-weight: 600; }
.param-table td { padding: 8px 10px; border-bottom: 1px solid var(--neutral-100, #f0f0f0); color: var(--neutral-700, #333); }
.param-table code { background: var(--neutral-100, #f0f0f0); padding: 1px 4px; border-radius: 3px; font-size: 11px; }
.code-block { background: #1e1e2e; color: #a6e3a1; padding: 14px; border-radius: 8px; font-size: 11px; overflow-x: auto; white-space: pre; font-family: monospace; }
</style>
