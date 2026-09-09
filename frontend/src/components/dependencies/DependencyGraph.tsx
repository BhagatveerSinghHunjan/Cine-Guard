"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";
import { toGraphData } from "@/lib/graph";
import type { AnalyzeResponse } from "@/types";

const FlowCanvas = dynamic(() => import("./FlowCanvas").then((m) => m.FlowCanvas), {
  ssr: false,
  loading: () => <p className="muted">Loading graph…</p>,
});

export function DependencyGraph({
  result,
  onSelectRisk,
  onSelectScene,
}: {
  result: AnalyzeResponse;
  onSelectRisk: (id: string) => void;
  onSelectScene: (sceneNumber: number) => void;
}) {
  const data = useMemo(
    () => toGraphData(result.risks, result.dependencies ?? [], result.analysis.scenes),
    [result],
  );
  if (data.nodes.length === 0) {
    return <p className="muted">No dependency data — no risks reference any scenes.</p>;
  }
  const riskCount = data.nodes.filter((n) => n.kind === "risk").length;
  const sceneCount = data.nodes.filter((n) => n.kind === "scene").length;
  return (
    <div className="graph-wrap">
      <div className="graph-head">
        <p className="muted">
          {riskCount} risk{riskCount === 1 ? "" : "s"} · {sceneCount} scene
          {sceneCount === 1 ? "" : "s"} · {data.edges.length} link
          {data.edges.length === 1 ? "" : "s"} — select a node for detail.
        </p>
        <ul className="graph-legend" aria-label="Graph legend">
          <li>
            <span className="legend-swatch legend-risk" aria-hidden="true" /> Risk
          </li>
          <li>
            <span className="legend-swatch legend-scene" aria-hidden="true" /> Scene
          </li>
          <li>
            <span className="legend-swatch legend-blocks" aria-hidden="true" /> Blocks
          </li>
        </ul>
      </div>
      <div className="graph-canvas">
        <FlowCanvas data={data} onSelectRisk={onSelectRisk} onSelectScene={onSelectScene} />
      </div>
      <div className="graph-fallback" aria-label="Dependency list fallback">
        <ul>
          {data.edges.map((e) => (
            <li key={e.id} className="muted">
              {e.source} —{e.label}→ {e.target}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
