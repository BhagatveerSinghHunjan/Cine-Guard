"use client";

import { useMemo, useState } from "react";
import { risksForScene, sceneRiskLevel } from "@/lib/selectors";
import type { AnalyzeResponse, Scene, Severity } from "@/types";

type Filter = "all" | Severity | "none";

const FILTERS: Array<{ id: Filter; label: string }> = [
  { id: "all", label: "All" },
  { id: "critical", label: "Critical" },
  { id: "high", label: "High Risk" },
  { id: "medium", label: "Medium Risk" },
  { id: "low", label: "Low Risk" },
  { id: "none", label: "No Risk" },
];

export function SceneList({
  result,
  onSelectScene,
}: {
  result: AnalyzeResponse;
  onSelectScene: (sceneNumber: number) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const scenes = useMemo(
    () => [...result.analysis.scenes].sort((a, b) => a.scene_number - b.scene_number),
    [result],
  );
  const visible = scenes.filter((s) => {
    const level = sceneRiskLevel(result.risks, s.scene_number);
    if (filter === "all") return true;
    if (filter === "none") return level === null;
    return level === filter;
  });
  return (
    <div>
      <div className="filter-row" role="group" aria-label="Filter scenes by risk level">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            className={`chip${filter === f.id ? " chip-active" : ""}`}
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="muted">No scenes match this filter.</p>
      ) : (
        <ul className="scene-list">
          {visible.map((s) => {
            const level = sceneRiskLevel(result.risks, s.scene_number);
            const count = risksForScene(result.risks, s.scene_number).length;
            return (
              <li key={s.scene_number}>
                <button
                  type="button"
                  className="scene-row"
                  onClick={() => onSelectScene(s.scene_number)}
                  aria-label={`Open Scene ${s.scene_number}: ${s.heading}`}
                >
                  <span className="scene-num">#{s.scene_number}</span>
                  <span className="scene-main">
                    <strong>{s.heading || "Untitled scene"}</strong>
                    <span className="muted">
                      {[
                        s.interior_or_exterior && s.interior_or_exterior !== "unknown"
                          ? s.interior_or_exterior.toUpperCase()
                          : null,
                        s.location,
                        s.time_of_day,
                        s.characters.length > 0 ? s.characters.join(", ") : null,
                      ]
                        .filter(Boolean)
                        .join(" · ") || "—"}
                    </span>
                  </span>
                  <span className={`badge badge-${level ?? "neutral"}`}>
                    {level ?? "no risk"}
                    {count > 0 ? ` · ${count}` : ""}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function SceneDetail({
  scene,
  result,
  onSelectRisk,
}: {
  scene: Scene;
  result: AnalyzeResponse;
  onSelectRisk: (id: string) => void;
}) {
  const risks = risksForScene(result.risks, scene.scene_number);
  return (
    <div className="risk-detail">
      <p className="muted">
        Scene #{scene.scene_number} · {scene.interior_or_exterior ?? "unknown"} ·{" "}
        {scene.time_of_day || "unknown time"}
      </p>
      <h3 className="risk-title">{scene.heading || "Untitled scene"}</h3>
      <dl className="detail-list">
        <div>
          <dt>Location</dt>
          <dd>{scene.location || "—"}</dd>
        </div>
        <div>
          <dt>Characters</dt>
          <dd>{scene.characters.length > 0 ? scene.characters.join(", ") : "—"}</dd>
        </div>
        <div>
          <dt>Production requirements</dt>
          <dd>
            {scene.production_requirements.length > 0
              ? scene.production_requirements.join(", ")
              : "—"}
          </dd>
        </div>
      </dl>
      {scene.description ? (
        <>
          <h4 className="detail-h">Description</h4>
          <p>{scene.description}</p>
        </>
      ) : null}
      <h4 className="detail-h">Associated risks ({risks.length})</h4>
      {risks.length === 0 ? (
        <p className="muted">No known risk for this scene.</p>
      ) : (
        <ul>
          {risks.map((r) => (
            <li key={r.id}>
              <button type="button" className="link-btn" onClick={() => onSelectRisk(r.id)}>
                {r.id} · {r.severity} · {r.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
