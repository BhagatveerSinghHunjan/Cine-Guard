"use client";

import { useState } from "react";
import { CategoryBadge, SeverityBadge } from "@/components/ui/Badge";
import {
  groupRisksBySeverity,
  riskSceneHeading,
  riskScenes,
  SEVERITY_ORDER,
} from "@/lib/selectors";
import type { Risk, Scene, Severity } from "@/types";
import { EvidenceList } from "./Evidence";

function sceneLabel(risk: Risk): string {
  const scenes = riskScenes(risk);
  if (scenes.length > 1) return `Scenes ${scenes.join(", ")}`;
  if (scenes.length === 1) return `Scene ${scenes[0]}`;
  return "Global";
}

export function RiskCard({
  risk,
  scenes,
  onSelect,
}: {
  risk: Risk;
  scenes?: Scene[];
  onSelect?: (id: string) => void;
}) {
  const heading = scenes ? riskSceneHeading(risk, scenes) : null;
  const inner = (
    <>
      <div className="risk-top">
        <SeverityBadge severity={risk.severity} />
        <CategoryBadge category={risk.category} />
        {risk.confidence ? (
          <span className="badge badge-neutral" title="Reasoning confidence">
            {risk.confidence} confidence
          </span>
        ) : null}
        {risk.status && risk.status !== "open" ? (
          <span className="badge badge-neutral">{risk.status}</span>
        ) : null}
        <span className="risk-scene">{sceneLabel(risk)}</span>
      </div>
      <h3 className="risk-title">{risk.title}</h3>
      {heading ? <p className="risk-heading">{heading}</p> : null}
      <p className="risk-desc">{risk.description}</p>
      {risk.why_it_matters && risk.why_it_matters !== risk.description ? (
        <p className="risk-rec">
          <strong>Why it matters:</strong> {risk.why_it_matters}
        </p>
      ) : null}
      <EvidenceList items={risk.evidence_items ?? []} fallback={risk.evidence} />
      {risk.recommendation ? (
        <p className="risk-rec">
          <strong>Recommendation:</strong> {risk.recommendation}
        </p>
      ) : null}
    </>
  );
  if (!onSelect) {
    return (
      <article className="risk-card" aria-label={`${risk.severity} risk: ${risk.title}`}>
        {inner}
      </article>
    );
  }
  return (
    <article className="risk-card" aria-label={`${risk.severity} risk: ${risk.title}`}>
      {inner}
      <button
        type="button"
        className="btn btn-ghost btn-sm risk-details-btn"
        onClick={() => onSelect(risk.id)}
        aria-label={`Open details for ${risk.title}`}
      >
        View details →
      </button>
    </article>
  );
}

export function RiskList({
  risks,
  scenes,
  onSelect,
}: {
  risks: Risk[];
  scenes?: Scene[];
  onSelect?: (id: string) => void;
}) {
  if (risks.length === 0) {
    return <p className="muted">No risks returned. The backend found nothing to flag.</p>;
  }
  return (
    <ul className="risk-list">
      {risks.map((r) => (
        <li key={r.id}>
          <RiskCard risk={r} scenes={scenes} onSelect={onSelect} />
        </li>
      ))}
    </ul>
  );
}

export function RiskSummary({ counts }: { counts: Record<string, number> }) {
  const items = SEVERITY_ORDER.map((k) => ({ key: k, value: counts[k] ?? 0 }));
  return (
    <dl className="risk-summary" aria-label="Risk summary">
      {items.map((it) => (
        <div key={it.key} className={`risk-stat risk-stat-${it.key}`}>
          <dt>{it.key}</dt>
          <dd>{it.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function RiskBoard({
  risks,
  scenes,
  onSelect,
}: {
  risks: Risk[];
  scenes?: Scene[];
  onSelect: (id: string) => void;
}) {
  const [filter, setFilter] = useState<"all" | Severity>("all");
  const groups = groupRisksBySeverity(risks);
  if (risks.length === 0) {
    return <p className="muted">No risks returned. The backend found nothing to flag.</p>;
  }
  return (
    <div>
      <div className="filter-row" role="group" aria-label="Filter risks by severity">
        {(["all", ...SEVERITY_ORDER] as const).map((s) => (
          <button
            key={s}
            type="button"
            className={`chip${filter === s ? " chip-active" : ""}`}
            aria-pressed={filter === s}
            onClick={() => setFilter(s)}
          >
            {s === "all" ? `All (${risks.length})` : `${s} (${groups[s].length})`}
          </button>
        ))}
      </div>
      <div className="risk-board">
        {SEVERITY_ORDER.filter((sev) => filter === "all" || filter === sev).map((sev) => (
          <section key={sev} aria-label={`${sev} risks`} className={`risk-group risk-group-${sev}`}>
            <h3 className="risk-group-h">
              {sev} <span className="dep-count">{groups[sev].length}</span>
            </h3>
            {groups[sev].length === 0 ? (
              <p className="muted">None</p>
            ) : (
              <ul className="risk-list">
                {groups[sev].map((r) => (
                  <li key={r.id}>
                    <RiskCard risk={r} scenes={scenes} onSelect={onSelect} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
