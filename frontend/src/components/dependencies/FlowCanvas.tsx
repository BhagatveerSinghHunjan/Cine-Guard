"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import type { GraphData } from "@/lib/graph";

function layout(data: GraphData): { nodes: Node[]; edges: Edge[] } {
  const risks = data.nodes.filter((n) => n.kind === "risk");
  const scenes = data.nodes.filter((n) => n.kind === "scene");
  const nodes: Node[] = [
    ...risks.map((n, i) => ({
      id: n.id,
      position: { x: 40, y: i * 130 },
      data: { label: nodeLabel(n) },
      className: `graph-node graph-node-risk-${n.severity ?? "low"}`,
    })),
    ...scenes.map((n, i) => ({
      id: n.id,
      position: { x: 420, y: i * 130 },
      data: { label: nodeLabel(n) },
      className: "graph-node graph-node-scene",
    })),
  ];
  const edges: Edge[] = data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: e.label === "blocks",
  }));
  return { nodes, edges };
}

function nodeLabel(n: { label: string; sublabel: string }) {
  return (
    <div>
      <strong>{n.label}</strong>
      <span>{n.sublabel}</span>
    </div>
  );
}

export function FlowCanvas({
  data,
  onSelectRisk,
  onSelectScene,
}: {
  data: GraphData;
  onSelectRisk: (id: string) => void;
  onSelectScene: (sceneNumber: number) => void;
}) {
  const { nodes, edges } = useMemo(() => layout(data), [data]);
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={(_, node) => {
        if (node.id.startsWith("risk:")) onSelectRisk(node.id.slice(5));
        else if (node.id.startsWith("scene:")) onSelectScene(Number(node.id.slice(6)));
      }}
      fitView
      attributionPosition="bottom-right"
    >
      <Background />
      <Controls />
      <MiniMap pannable zoomable />
    </ReactFlow>
  );
}
