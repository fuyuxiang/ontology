import type { PublishGate } from '../types/builder'

// ── 资产扫描 6 步（UI 步骤枚举，与具体业务无关） ──
export const SCAN_STEPS = [
  { key: 'intent', label: '识别用户需求', description: '解析场景关键词与业务意图...' },
  { key: 'sensitive', label: '敏感词检测', description: '安全过滤与合规校验...' },
  { key: 'deep_parse', label: '需求深度解析', description: '语义理解与实体抽取...' },
  { key: 'radar_scan', label: '结构化资产扫描', description: '扫描数据模型、标签、指标...' },
  { key: 'doc_scan', label: '非结构化文档检索', description: '检索业务文档、知识库...' },
  { key: 'compose', label: '规范回答', description: '组装资产清单与匹配说明...' },
]

// ── 网络构建动画阶段（UI 动画文案） ──
export const GRAPH_BUILDING_STEPS = [
  '🔍 识别业务主体...',
  '🏷️ 关联本体属性...',
  '🔗 建立关系连线...',
  '⚙️ 生成触发条件...',
  '⚡ 编排执行动作...',
]

// ── 水合演练 4 阶段（UI 阶段枚举） ──
export const HYDRATION_PHASES = [
  { key: 'ingest' as const, label: '数据接入', color: '#6366f1' },
  { key: 'instantiate' as const, label: '本体实例化', color: '#2E5BFF' },
  { key: 'match' as const, label: '关系映射验证', color: '#f59e0b' },
  { key: 'strategy' as const, label: '策略输出', color: '#10b981' },
]

// ── 发布门禁（默认结构，业务实例数据不在此定义） ──
export const DEFAULT_PUBLISH_GATES: PublishGate[] = [
  { key: 'structure', label: '本体结构完整', desc: '本体 0 个', pass: false },
  { key: 'drill', label: '水合演练通过', desc: '未演练', pass: false },
  { key: 'version_ready', label: '版本就绪', desc: '版本号自动生成', pass: true },
]
