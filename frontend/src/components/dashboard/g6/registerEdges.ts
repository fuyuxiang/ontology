import { register, BaseEdge, ExtensionCategory } from '@antv/g6'
import { COLORS } from './darkTheme'

/**
 * 流动动画边 — 默认暗灰虚线，高亮时绿色 + ant-line 流动
 */
class FlowEdge extends BaseEdge {
  getKeyStyle(attributes: any) {
    return {
      ...super.getKeyStyle(attributes),
      stroke: attributes.highlighted ? COLORS.edgeHighlight : COLORS.edgeDefault,
      lineWidth: attributes.highlighted ? 2 : 1,
      strokeOpacity: attributes.dimmed ? 0.1 : 0.7,
      lineDash: attributes.highlighted ? [6, 4] : [4, 4],
      endArrow: true,
      endArrowSize: 6,
      endArrowFill: attributes.highlighted ? COLORS.edgeHighlight : COLORS.edgeDefault,
    }
  }

  getLabelStyle(attributes: any) {
    if (!attributes.highlighted) return false as any
    return {
      ...super.getLabelStyle(attributes),
      text: attributes.label || '',
      fill: COLORS.labelSecondary,
      fontSize: 9,
      fontFamily: 'Inter Variable, Noto Sans SC, system-ui, sans-serif',
      background: {
        fill: 'rgba(15,23,42,0.85)',
        padding: [3, 6, 3, 6],
        radius: 4,
      },
    }
  }
}

export function registerCustomEdges() {
  register(ExtensionCategory.EDGE, 'flow-edge', FlowEdge)
}
