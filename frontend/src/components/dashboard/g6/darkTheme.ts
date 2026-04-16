/** G6 v5 深色主题配置 */
export const DARK_BG = '#0F172A'

export const COLORS = {
  bg: DARK_BG,
  nodeFill: '#1E293B',
  nodeStroke: '#334155',
  nodeStrokeHover: '#10B981',
  labelPrimary: '#E2E8F0',
  labelSecondary: '#94A3B8',
  edgeDefault: '#334155',
  edgeHighlight: '#10B981',
  edgeDim: 'rgba(51,65,85,.2)',
  nodeDim: 'rgba(30,41,59,.3)',
  // Tier 颜色
  tier1: '#5C7CFA', // 核心对象 - 蓝
  tier2: '#20C997', // 领域对象 - 绿
  tier3: '#F59F00', // 场景对象 - 橙
  // 状态颜色
  statusActive: '#12B886',
  statusWarning: '#F59F00',
  statusError: '#FA5252',
} as const

export function tierColor(tier: number) {
  if (tier === 1) return COLORS.tier1
  if (tier === 2) return COLORS.tier2
  return COLORS.tier3
}

export function statusColor(status: string) {
  if (status === 'active') return COLORS.statusActive
  if (status === 'warning') return COLORS.statusWarning
  return COLORS.statusError
}
