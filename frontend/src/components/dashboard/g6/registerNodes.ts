import { register, BaseNode, ExtensionCategory } from '@antv/g6'
import { COLORS, tierColor, statusColor } from './darkTheme'

/**
 * DataSource 节点 — 圆角矩形，蓝色调，数据库图标
 */
class DataSourceNode extends BaseNode {
  get defaultStyle() {
    return {
      ...super.defaultStyle,
    }
  }

  getKeyStyle(attributes: any) {
    const tier = attributes.tier ?? 1
    return {
      ...super.getKeyStyle(attributes),
      width: 140,
      height: 56,
      radius: 10,
      fill: COLORS.nodeFill,
      stroke: tierColor(tier),
      strokeOpacity: 0.6,
      lineWidth: 1.5,
      shadowColor: 'rgba(0,0,0,0.45)',
      shadowBlur: 10,
      shadowOffsetY: 4,
    }
  }

  getIconStyle(attributes: any) {
    return {
      ...super.getIconStyle(attributes),
      src: '',
      text: '\u{1F4BE}',
      fontSize: 16,
      textAlign: 'center',
      textBaseline: 'middle',
      dx: -50,
      dy: -6,
    }
  }

  getLabelStyle(attributes: any) {
    return {
      ...super.getLabelStyle(attributes),
      text: attributes.label || '',
      fill: COLORS.labelPrimary,
      fontSize: 12,
      fontWeight: 600,
      fontFamily: 'Inter Variable, Noto Sans SC, system-ui, sans-serif',
      textAlign: 'left',
      dx: -32,
      dy: -8,
    }
  }

  getBadgesStyle(attributes: any) {
    const status = attributes.status || 'active'
    return [
      {
        text: '',
        fill: statusColor(status),
        r: 4,
        placement: 'right-top' as const,
        offsetX: -6,
        offsetY: 6,
      },
    ]
  }
}

/**
 * Operator 节点 — 六边形，绿色调，齿轮图标
 */
class OperatorNode extends BaseNode {
  getKeyStyle(attributes: any) {
    const tier = attributes.tier ?? 2
    return {
      ...super.getKeyStyle(attributes),
      width: 140,
      height: 56,
      radius: 10,
      fill: COLORS.nodeFill,
      stroke: tierColor(tier),
      strokeOpacity: 0.6,
      lineWidth: 1.5,
      shadowColor: 'rgba(0,0,0,0.45)',
      shadowBlur: 10,
      shadowOffsetY: 4,
    }
  }

  getIconStyle(attributes: any) {
    return {
      ...super.getIconStyle(attributes),
      text: '\u2699',
      fontSize: 16,
      textAlign: 'center',
      textBaseline: 'middle',
      dx: -50,
      dy: -6,
    }
  }

  getLabelStyle(attributes: any) {
    return {
      ...super.getLabelStyle(attributes),
      text: attributes.label || '',
      fill: COLORS.labelPrimary,
      fontSize: 12,
      fontWeight: 600,
      fontFamily: 'Inter Variable, Noto Sans SC, system-ui, sans-serif',
      textAlign: 'left',
      dx: -32,
      dy: -8,
    }
  }

  getBadgesStyle(attributes: any) {
    const status = attributes.status || 'active'
    return [
      {
        text: '',
        fill: statusColor(status),
        r: 4,
        placement: 'right-top' as const,
        offsetX: -6,
        offsetY: 6,
      },
    ]
  }
}

/**
 * ModelService 节点 — 圆角矩形，橙色调，闪电图标
 */
class ModelServiceNode extends BaseNode {
  getKeyStyle(attributes: any) {
    const tier = attributes.tier ?? 3
    return {
      ...super.getKeyStyle(attributes),
      width: 140,
      height: 56,
      radius: 10,
      fill: COLORS.nodeFill,
      stroke: tierColor(tier),
      strokeOpacity: 0.6,
      lineWidth: 1.5,
      shadowColor: 'rgba(0,0,0,0.45)',
      shadowBlur: 10,
      shadowOffsetY: 4,
    }
  }

  getIconStyle(attributes: any) {
    return {
      ...super.getIconStyle(attributes),
      text: '\u26A1',
      fontSize: 16,
      textAlign: 'center',
      textBaseline: 'middle',
      dx: -50,
      dy: -6,
    }
  }

  getLabelStyle(attributes: any) {
    return {
      ...super.getLabelStyle(attributes),
      text: attributes.label || '',
      fill: COLORS.labelPrimary,
      fontSize: 12,
      fontWeight: 600,
      fontFamily: 'Inter Variable, Noto Sans SC, system-ui, sans-serif',
      textAlign: 'left',
      dx: -32,
      dy: -8,
    }
  }

  getBadgesStyle(attributes: any) {
    const status = attributes.status || 'active'
    return [
      {
        text: '',
        fill: statusColor(status),
        r: 4,
        placement: 'right-top' as const,
        offsetX: -6,
        offsetY: 6,
      },
    ]
  }
}

export function registerCustomNodes() {
  register(ExtensionCategory.NODE, 'datasource-node', DataSourceNode)
  register(ExtensionCategory.NODE, 'operator-node', OperatorNode)
  register(ExtensionCategory.NODE, 'model-node', ModelServiceNode)
}
