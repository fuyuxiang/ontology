import { renderMarkdownSafe } from './sanitize'

// 判断一段文本是否包含 markdown 结构（表格、标题、列表、引用、代码块）
// 用于决定是否展示「下载 HTML」按钮——纯文本闲聊不展示
export function looksLikeMarkdown(content: string): boolean {
  if (!content) return false
  const patterns = [
    /^\s{0,3}#{1,6}\s+\S/m, // 标题
    /^\s*\|.+\|\s*$/m, // 表格行
    /^\s*```/m, // 代码块
    /^\s{0,3}>\s+\S/m, // 引用
    /^\s*[-*+]\s+\S/m, // 无序列表
    /^\s*\d+\.\s+\S/m, // 有序列表
  ]
  return patterns.some((re) => re.test(content))
}

// 完整 HTML 文档的样式：表格、标题、引用、代码块的精美排版
const DOCUMENT_STYLE = `
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 40px 24px;
    background: #f3f4f6;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
      "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    color: #1f2937;
    line-height: 1.7;
  }
  .doc {
    max-width: 920px;
    margin: 0 auto;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 8px 24px rgba(0, 0, 0, 0.06);
    padding: 48px 56px;
  }
  .doc h1 { font-size: 28px; font-weight: 700; margin: 0 0 20px; padding-bottom: 12px; border-bottom: 2px solid #e5e7eb; }
  .doc h2 { font-size: 22px; font-weight: 600; margin: 32px 0 14px; color: #111827; }
  .doc h3 { font-size: 18px; font-weight: 600; margin: 24px 0 10px; color: #374151; }
  .doc h4 { font-size: 15px; font-weight: 600; margin: 18px 0 8px; color: #4b5563; }
  .doc p { margin: 10px 0; }
  .doc a { color: #2563eb; text-decoration: none; }
  .doc a:hover { text-decoration: underline; }
  .doc table {
    width: 100%;
    border-collapse: collapse;
    margin: 18px 0;
    font-size: 14px;
    box-shadow: 0 0 0 1px #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
  }
  .doc thead { background: #f9fafb; }
  .doc th, .doc td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #e5e7eb; }
  .doc th { font-weight: 600; color: #374151; white-space: nowrap; }
  .doc tbody tr:last-child td { border-bottom: none; }
  .doc tbody tr:nth-child(even) { background: #fafafa; }
  .doc tbody tr:hover { background: #f0f7ff; }
  .doc blockquote {
    margin: 16px 0;
    padding: 8px 18px;
    border-left: 4px solid #93c5fd;
    background: #eff6ff;
    color: #1e40af;
    border-radius: 0 6px 6px 0;
  }
  .doc blockquote p { margin: 6px 0; }
  .doc code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 13px;
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 4px;
    color: #be123c;
  }
  .doc pre {
    background: #1e293b;
    color: #e2e8f0;
    padding: 16px 18px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.5;
  }
  .doc pre code { background: none; color: inherit; padding: 0; }
  .doc ul, .doc ol { padding-left: 24px; margin: 10px 0; }
  .doc li { margin: 4px 0; }
  .doc hr { border: none; border-top: 1px solid #e5e7eb; margin: 28px 0; }
  .doc img { max-width: 100%; }
  .doc__footer {
    max-width: 920px;
    margin: 20px auto 0;
    text-align: center;
    font-size: 12px;
    color: #9ca3af;
  }
`

// 把 markdown 文本渲染为一份独立、带样式的 HTML 文档字符串
export function buildHtmlDocument(markdown: string, title = '智能体分析报告'): string {
  const bodyHtml = renderMarkdownSafe(markdown)
  const safeTitle = title.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c] as string)
  const stamp = new Date().toLocaleString('zh-CN')
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${safeTitle}</title>
<style>${DOCUMENT_STYLE}</style>
</head>
<body>
<div class="doc">
${bodyHtml}
</div>
<div class="doc__footer">由智能体对话测试导出 · ${stamp}</div>
</body>
</html>`
}

// 复制文本到剪贴板，返回是否成功（兼容不支持 Clipboard API 的环境）
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    /* 回退到 execCommand */
  }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}

// 触发浏览器下载 HTML 文件
export function downloadHtml(markdown: string, title = '智能体分析报告'): void {
  const html = buildHtmlDocument(markdown, title)
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  a.href = url
  a.download = `${title}-${ts}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
