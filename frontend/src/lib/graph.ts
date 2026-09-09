import type { Risk, RiskDependency, Scene } from "@/types";

export type GraphNodeKind = "risk" | "scene";

export interface GraphNodeDatum {
  id: string;
  kind: GraphNodeKind;
  label: string;
  sublabel: string;
  severity?: string;
  refId: string | number;
}

export interface GraphEdgeDatum {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface GraphData {
  nodes: GraphNodeDatum[];
  edges: GraphEdgeDatum[];
}

function riskScenes(risk: Risk): number[] {
  const scenes = new Set<number>(risk.affected_scenes ?? []);
  if (typeof risk.scene_number === "number") scenes.add(risk.scene_number);
  return [...scenes].sort((a, b) => a - b);
}

/**
 * Pure transform: backend risks + dependency edges + scenes → graph data.
 * Scene nodes exist only for scenes referenced by at least one risk, plus
 * edges risk→scene ("affects") so the cascade reads location → scene → risk.
 */
export function toGraphData(
  risks: Risk[],
  dependencies: RiskDependency[],
  scenes: Scene[],
): GraphData {
  const nodes: GraphNodeDatum[] = [];
  const edges: GraphEdgeDatum[] = [];
  const sceneByNumber = new Map(scenes.map((s) => [s.scene_number, s]));
  const referencedScenes = new Set<number>();
  for (const r of risks) for (const n of riskScenes(r)) referencedScenes.add(n);

  for (const n of [...referencedScenes].sort((a, b) => a - b)) {
    const scene = sceneByNumber.get(n);
    nodes.push({
      id: `scene:${n}`,
      kind: "scene",
      label: `Scene ${n}`,
      sublabel: scene?.location || "Unknown location",
      refId: n,
    });
  }
  for (const r of risks) {
    nodes.push({
      id: `risk:${r.id}`,
      kind: "risk",
      label: r.title,
      sublabel: `${r.severity} · ${r.category}`,
      severity: r.severity,
      refId: r.id,
    });
    for (const n of riskScenes(r)) {
      edges.push({
        id: `e-risk:${r.id}-scene:${n}`,
        source: `risk:${r.id}`,
        target: `scene:${n}`,
        label: "affects",
      });
    }
  }
  for (const d of dependencies ?? []) {
    edges.push({
      id: `e-${d.id}`,
      source: `risk:${d.source_risk_id}`,
      target: `risk:${d.target_risk_id}`,
      label: d.relationship,
    });
  }
  return { nodes, edges };
}
