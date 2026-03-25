import { useEffect, useRef, useState, type PointerEvent, type WheelEvent } from "react";

import type { GraphData, GraphNode, RiskLevel } from "../types";

interface GraphCanvasProps {
  graph: GraphData;
  selectedNodeId?: string | null;
  onSelectNode?: (node: GraphNode) => void;
  riskByNodeId?: Partial<Record<string, RiskLevel>>;
  showEdgeLabels?: boolean;
  showControls?: boolean;
}

interface Point {
  x: number;
  y: number;
}

interface ViewBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

const WIDTH = 920;
const HEIGHT = 560;
const PADDING = 120;
const MIN_ZOOM_FACTOR = 0.18;

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

export const RISK_COLORS: Record<RiskLevel, string> = {
  HIGH: "#ff4d4f",
  MEDIUM: "#fa8c16",
  LOW: "#52c41a",
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
    User: { x: 220, y: 220, radiusX: 140, radiusY: 100 },
    PortingQuery: { x: 640, y: 120, radiusX: 90, radiusY: 56 },
    Contract: { x: 710, y: 210, radiusX: 90, radiusY: 56 },
    Billing: { x: 710, y: 350, radiusX: 90, radiusY: 56 },
    CustomerService: { x: 530, y: 470, radiusX: 90, radiusY: 56 },
    RetentionAction: { x: 820, y: 410, radiusX: 60, radiusY: 60 },
    NetworkUsage: { x: 500, y: 120, radiusX: 90, radiusY: 56 },
    Interaction: { x: 650, y: 180, radiusX: 110, radiusY: 70 },
    Result: { x: 450, y: 90, radiusX: 80, radiusY: 40 },
    RiskResult: { x: 450, y: 90, radiusX: 80, radiusY: 40 },
    Entity: { x: 260, y: 440, radiusX: 90, radiusY: 56 },
    Inference: { x: 640, y: 430, radiusX: 110, radiusY: 70 },
    Action: { x: 840, y: 320, radiusX: 50, radiusY: 64 },
  };

  return new Map(
    Array.from(groups.entries()).flatMap(([type, items]) => {
      const anchor = anchors[type] ?? { x: WIDTH / 2, y: HEIGHT / 2, radiusX: 120, radiusY: 90 };
      return items.map((node, index) => {
        const spread = Math.max(items.length - 1, 1);
        const angle = -Math.PI * 0.8 + (index / spread) * Math.PI * 0.8;
        const x = clamp(anchor.x + Math.cos(angle) * anchor.radiusX, 60, WIDTH - 60);
        const y = clamp(anchor.y + Math.sin(angle) * anchor.radiusY, 60, HEIGHT - 60);
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

function buildGraphBounds(graph: GraphData, positions: Map<string, Point>): ViewBox {
  if (!graph.nodes.length) {
    return { x: 0, y: 0, width: WIDTH, height: HEIGHT };
  }

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const node of graph.nodes) {
    const position = positions.get(node.id);
    if (!position) {
      continue;
    }
    const radius = node.type === "User" ? 28 : 22;
    minX = Math.min(minX, position.x - radius);
    minY = Math.min(minY, position.y - radius);
    maxX = Math.max(maxX, position.x + radius);
    maxY = Math.max(maxY, position.y + radius);
  }

  if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) {
    return { x: 0, y: 0, width: WIDTH, height: HEIGHT };
  }

  return {
    x: minX - PADDING,
    y: minY - PADDING,
    width: Math.max(maxX - minX + PADDING * 2, WIDTH),
    height: Math.max(maxY - minY + PADDING * 2, HEIGHT),
  };
}

function clampViewBox(viewBox: ViewBox, initialViewBox: ViewBox): ViewBox {
  const width = clamp(viewBox.width, initialViewBox.width * MIN_ZOOM_FACTOR, initialViewBox.width);
  const height = clamp(viewBox.height, initialViewBox.height * MIN_ZOOM_FACTOR, initialViewBox.height);
  const maxX = initialViewBox.x + initialViewBox.width - width;
  const maxY = initialViewBox.y + initialViewBox.height - height;

  return {
    x: clamp(viewBox.x, initialViewBox.x, maxX),
    y: clamp(viewBox.y, initialViewBox.y, maxY),
    width,
    height,
  };
}

function shortLabel(label: string) {
  const value = label.includes("/") ? label.split("/").pop() || label : label;
  return value.length > 8 ? `${value.slice(0, 8)}..` : value;
}

export function GraphCanvas({
  graph,
  selectedNodeId,
  onSelectNode,
  riskByNodeId,
  showEdgeLabels = false,
  showControls = true,
}: GraphCanvasProps) {
  const positions = resolvePositions(graph);
  const initialViewBox = buildGraphBounds(graph, positions);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const dragRef = useRef<{ pointerId: number; clientX: number; clientY: number; moved: boolean } | null>(null);
  const dragMovedRef = useRef(false);
  const [viewBox, setViewBox] = useState<ViewBox>(initialViewBox);
  const viewBoxRef = useRef(viewBox);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    setViewBox(initialViewBox);
    dragRef.current = null;
    dragMovedRef.current = false;
    setIsDragging(false);
  }, [initialViewBox.x, initialViewBox.y, initialViewBox.width, initialViewBox.height]);

  useEffect(() => {
    viewBoxRef.current = viewBox;
  }, [viewBox]);

  function applyZoom(factor: number, clientX?: number, clientY?: number) {
    const svg = svgRef.current;
    const rect = svg?.getBoundingClientRect();
    const current = viewBoxRef.current;
    const relativeX = rect && clientX !== undefined ? clamp((clientX - rect.left) / rect.width, 0, 1) : 0.5;
    const relativeY = rect && clientY !== undefined ? clamp((clientY - rect.top) / rect.height, 0, 1) : 0.5;
    const nextWidth = current.width * factor;
    const nextHeight = current.height * factor;
    const focusX = current.x + current.width * relativeX;
    const focusY = current.y + current.height * relativeY;

    setViewBox(
      clampViewBox(
        {
          x: focusX - nextWidth * relativeX,
          y: focusY - nextHeight * relativeY,
          width: nextWidth,
          height: nextHeight,
        },
        initialViewBox,
      ),
    );
  }

  function resetViewBox() {
    setViewBox(initialViewBox);
    dragMovedRef.current = false;
  }

  function handleWheel(event: WheelEvent<SVGSVGElement>) {
    event.preventDefault();
    applyZoom(event.deltaY < 0 ? 0.88 : 1.14, event.clientX, event.clientY);
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    if (event.button !== 0) {
      return;
    }
    dragRef.current = {
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      moved: false,
    };
    dragMovedRef.current = false;
    setIsDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<SVGSVGElement>) {
    const dragState = dragRef.current;
    const svg = svgRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId || !svg) {
      return;
    }

    const rect = svg.getBoundingClientRect();
    const current = viewBoxRef.current;
    const moveX = event.clientX - dragState.clientX;
    const moveY = event.clientY - dragState.clientY;
    const dx = (moveX / rect.width) * current.width;
    const dy = (moveY / rect.height) * current.height;

    if (Math.abs(moveX) > 2 || Math.abs(moveY) > 2) {
      dragState.moved = true;
    }

    setViewBox(
      clampViewBox(
        {
          ...current,
          x: current.x - dx,
          y: current.y - dy,
        },
        initialViewBox,
      ),
    );

    dragState.clientX = event.clientX;
    dragState.clientY = event.clientY;
  }

  function finishDrag(event: PointerEvent<SVGSVGElement>) {
    const dragState = dragRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId) {
      return;
    }
    dragMovedRef.current = dragState.moved;
    dragRef.current = null;
    setIsDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handleNodeClick(node: GraphNode) {
    if (dragMovedRef.current) {
      dragMovedRef.current = false;
      return;
    }
    onSelectNode?.(node);
  }

  return (
    <>
      {showControls ? (
        <>
          <div className="graph-toolbar">
            <button type="button" className="graph-tool-btn" onClick={() => applyZoom(0.82)}>
              +
            </button>
            <button type="button" className="graph-tool-btn" onClick={() => applyZoom(1.22)}>
              -
            </button>
            <button type="button" className="graph-tool-btn reset" onClick={resetViewBox}>
              重置
            </button>
          </div>
          <div className="graph-tip">滚轮缩放，拖动画布平移</div>
        </>
      ) : null}

      <svg
        ref={svgRef}
        className={`graph-svg ${isDragging ? "is-dragging" : ""}`}
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="知识图谱"
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishDrag}
        onPointerCancel={finishDrag}
      >
        {graph.edges.map((edge) => {
          const source = positions.get(edge.source);
          const target = positions.get(edge.target);
          if (!source || !target) {
            return null;
          }
          const midX = (source.x + target.x) / 2;
          const midY = (source.y + target.y) / 2;
          return (
            <g key={`${edge.source}-${edge.target}-${edge.label}`}>
              <line className="graph-link" x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
              {showEdgeLabels ? (
                <>
                  <rect
                    className="graph-edge-label-bg"
                    x={midX - Math.max(edge.label.length * 3.6, 20)}
                    y={midY - 10}
                    rx={8}
                    ry={8}
                    width={Math.max(edge.label.length * 7.2, 40)}
                    height={20}
                  />
                  <text className="graph-edge-label" x={midX} y={midY + 4} textAnchor="middle">
                    {edge.label}
                  </text>
                </>
              ) : null}
            </g>
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
          const riskLevel = riskByNodeId?.[node.id];
          const riskStroke = riskLevel ? RISK_COLORS[riskLevel] : null;

          return (
            <g
              key={node.id}
              className={`graph-node ${isSelected ? "is-selected" : ""}`}
              transform={`translate(${position.x}, ${position.y})`}
              onClick={() => handleNodeClick(node)}
            >
              <title>{node.label || node.id}</title>
              {riskStroke ? (
                <circle className="graph-risk-ring" r={radius + 8} fill="none" stroke={riskStroke} strokeWidth={4} strokeOpacity={0.82} />
              ) : null}
              <circle className="graph-node-core" r={radius} fill={fill} stroke="#ffffff" strokeWidth={isSelected ? 4 : 2} />
              <text textAnchor="middle" dy="0.35em" fill="#ffffff" fontSize="9px" fontWeight="500">
                {shortLabel(node.label || node.id)}
              </text>
            </g>
          );
        })}
      </svg>
    </>
  );
}
