import DOMPurify from 'dompurify'
import { marked } from 'marked'

export function renderMarkdownSafe(content: string): string {
  const raw = marked.parse(content) as string
  return DOMPurify.sanitize(raw)
}
