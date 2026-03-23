import type { GraphData, GraphNode } from "../types";

interface GraphCanvasProps {
  graph: GraphData;
  selectedNodeId?: string | null;
  onSelectNode?: (node: GraphNode) => void;
}

const WIDTH = 920;
const HEIGHT = 560;

export const NODE_TYPE_COLORS: Record<string, string> = {
  Source: "#1890ff",
  Class: "#52c41a",
  Inference: "#722ed1",
  Result: "#fa8c16",
  RiskResult: "#fa8c16",
  Entity: "#13c2c2",
  User: "#1890ff",
  PortingQuery: "#36cfc9",
  Contract: "#73d13d",
  Billing: "#faad14",
  NetworkUsage: "#597ef7",
  CustomerService: "#ff7a45",
  RetentionAction: "#eb2f96",
  Interaction: "#52c41a",
  Action: "#13c2c2",
};

export const NODE_TYPE_LABELS: Record<string, string> = {
  Source: "数据源",
  Class: "本体类",
  Inference: "推理结果",
  Result: "查询结果",
  RiskResult: "风险结果",
  Entity: "实体",
  User: "用户",
  PortingQuery: "携转资格",
  Contract: "业务合约",
  Billing: "账务信息",
  NetworkUsage: "网络使用",
  CustomerService: "客服交互",
  RetentionAction: "维系动作",
  Interaction: "交互记录",
  Action: "动作",
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function buildFallbackPositions(nodes: GraphNode[]) {
  const groups = new Map<string, GraphNode[]>();
  for (const node of nodes) {
    const bucket = groups.get(node.type) ?? [];
    bucket.push(node);
    groups.set(node.type, bucket);
  }

  const anchors: Record<string, { x: number; y: number; radiusX: number; radiusY: number }> = {
    User: { x: 0.24, y: 0.38, radiusX: 0.2, radiusY: 0.18 },
    PortingQuery: { x: 0.74, y: 0.22, radiusX: 0.12, radiusY: 0.08 },
    Contract: { x: 0.78, y: 0.38, radiusX: 0.12, radiusY: 0.08 },
    Billing: { x: 0.74, y: 0.58, radiusX: 0.12, radiusY: 0.08 },
    CustomerService: { x: 0.58, y: 0.76, radiusX: 0.12, radiusY: 0.08 },
    RetentionAction: { x: 0.88, y: 0.7, radiusX: 0.08, radiusY: 0.08 },
    NetworkUsage: { x: 0.56, y: 0.2, radiusX: 0.12, radiusY: 0.08 },
    Interaction: { x: 0.72, y: 0.32, radiusX: 0.16, radiusY: 0.12 },
    Result: { x: 0.52, y: 0.18, radiusX: 0.14, radiusY: 0.06 },
    RiskResult: { x: 0.52, y: 0.18, radiusX: 0.14, radiusY: 0.06 },
    Entity: { x: 0.28, y: 0.78, radiusX: 0.12, radiusY: 0.08 },
    Inference: { x: 0.7, y: 0.74, radiusX: 0.16, radiusY: 0.1 },
    Action: { x: 0.9, y: 0.58, radiusX: 0.06, radiusY: 0.08 },
  };

  return new Map(
    Array.from(groups.entries()).flatMap(([type, items]) => {
      const anchor = anchors[type] ?? { x: 0.5, y: 0.5, radiusX: 0.2, radiusY: 0.16 };
      return items.map((node, index) => {
        const spread = Math.max(items.length - 1, 1);
        const angle = -Math.PI * 0.8 + (index / spread) * Math.PI * 0.8;
        const x = clamp(anchor.x + Math.cos(angle) * anchor.radiusX, 0.06, 0.94);
        const y = clamp(anchor.y + Math.sin(angle) * anchor.radiusY, 0.08, 0.92);
        return [node.id, { x, y }] as const;
      });
    }),
  );
}

function resolvePositions(graph: GraphData) {
  const hasCoordinates = graph.nodes.every((node) => typeof node.x === "number" && typeof node.y === "number");
  if (hasCoordinates) {
    return new Map(
      graph.nodes.map((node) => [
        node.id,
        {
          x: node.x as number,
          y: node.y as number,
        },
      ]),
    );
  }
  return buildFallbackPositions(graph.nodes);
}

function shortLabel(label: string) {
  const value = label.includes("/") ? label.split("/").pop() || label : label;
  return value.length > 8 ? `${value.slice(0, 8)}..` : value;
}

export function GraphCanvas({ graph, selectedNodeId, onSelectNode }: GraphCanvasProps) {
  const positions = resolvePositions(graph);

  return (
    <svg className="graph-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="知识图谱">
      {graph.edges.map((edge) => {
        const source = positions.get(edge.source);
        const target = positions.get(edge.target);
        if (!source || !target) {
          return null;
        }
        return (
          <line
            key={`${edge.source}-${edge.target}-${edge.label}`}
            className="graph-link"
            x1={source.x * WIDTH}
            y1={source.y * HEIGHT}
            x2={target.x * WIDTH}
            y2={target.y * HEIGHT}
          />
        );
      })}

      {graph.nodes.map((node) => {
        const position = positions.get(node.id);
        if (!position) {
          return null;
        }

        const fill = NODE_TYPE_COLORS[node.type] || "#999999";
        const radius = node.type === "User" ? 20 : 16;
        const isSelected = selectedNodeId === node.id;

        return (
          <g
            key={node.id}
            className={`graph-node ${isSelected ? "is-selected" : ""}`}
            transform={`translate(${position.x * WIDTH}, ${position.y * HEIGHT})`}
            onClick={() => onSelectNode?.(node)}
          >
            <title>{node.label || node.id}</title>
            <circle r={radius} fill={fill} stroke="#ffffff" strokeWidth={isSelected ? 4 : 2} />
            <text textAnchor="middle" dy="0.35em" fill="#ffffff" fontSize="9px" fontWeight="500">
              {shortLabel(node.label || node.id)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
