"use client";

import { CategoryBadge, SeverityBadge } from "@/components/ui/Badge";
import { dependenciesForRisk, recommendationsForRisk, riskScenes } from "@/lib/selectors";
import type { AnalyzeResponse, Risk } from "@/types";
import { EvidenceList } from "./Evidence";

export function RiskDetail({
  risk,
  result,
  onSelectRisk,
  onSelectScene,
}: {
  risk: Risk;
  result: AnalyzeResponse;
  onSelectRisk: (id: string) => void;
  onSelectScene: (sceneNumber: number) => void;
}) {
  const scenes = riskScenes(risk);
  const recs = recommendationsForRisk(result.recommendations, risk.id);
  const edges = dependenciesForRisk(result.dependencies, risk.id);
  const byId = new Map(result.risks.map((r) => [r.id, r]));
  const knownFacts = (risk.evidence_items ?? []).filter((e) => e.kind === "screenplay");
  const researchSources = (risk.evidence_items ?? []).filter(
    (e) => e.kind === "research" && (e.source_title || e.source_url),
  );
  const seenSources = new Map<string, (typeof researchSources)[number]>();
  for (const s of researchSources) {
    const key = s.source_url || s.source_title;
    if (key && !seenSources.has(key)) seenSources.set(key, s);
  }
  const unknowns = result.analysis.unknowns ?? [];
  const confidenceNote =
    risk.confidence === "low" || risk.status === "unknown"
      ? "Confidence here is limited — treat this risk as provisional until confirmed."
      : null;
  return (
    <div className="risk-detail">
      <div className="risk-top">
        <SeverityBadge severity={risk.severity} />
        <CategoryBadge category={risk.category} />
        {risk.confidence ? (
          <span className="badge badge-neutral">{risk.confidence} confidence</span>
        ) : null}
        {risk.status ? <span className="badge badge-neutral">{risk.status}</span> : null}
      </div>
      <h3 className="risk-title">{risk.title}</h3>

      <dl className="detail-list">
        <div>
          <dt>Affected scenes</dt>
          <dd>
            {scenes.length === 0 ? (
              "Global"
            ) : (
              <span className="scene-links">
                {scenes.map((n) => (
                  <button
                    key={n}
                    type="button"
                    className="link-btn"
                    onClick={() => onSelectScene(n)}
                  >
                    Scene {n}
                  </button>
                ))}
              </span>
            )}
          </dd>
        </div>
        {(risk.affected_dependencies ?? []).length > 0 ? (
          <div>
            <dt>Affected dependencies</dt>
            <dd>{(risk.affected_dependencies ?? []).join(", ")}</dd>
          </div>
        ) : null}
      </dl>

      <h4 className="detail-h">Description</h4>
      <p>{risk.description}</p>
      {risk.why_it_matters ? (
        <>
          <h4 className="detail-h">Why this matters</h4>
          <p>{risk.why_it_matters}</p>
        </>
      ) : null}

      <h4 className="detail-h">Evidence</h4>
      <EvidenceList items={risk.evidence_items ?? []} fallback={risk.evidence} />

      {seenSources.size > 0 ? (
        <>
          <h4 className="detail-h">Source</h4>
          <ul>
            {[...seenSources.values()].map((s) => (
              <li key={s.source_url || s.source_title}>
                {s.source_title ? <strong>{s.source_title}</strong> : null}
                {s.source_domain ? ` · ${s.source_domain}` : null}
                {s.provider ? ` · via ${s.provider}` : null}{" "}
                {s.source_url ? (
                  <a href={s.source_url} target="_blank" rel="noreferrer">
                    {s.source_url}
                  </a>
                ) : null}
                {s.retrieved_at ? (
                  <span className="muted"> · retrieved {s.retrieved_at.slice(0, 10)}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      <h4 className="detail-h">What we know</h4>
      {knownFacts.length > 0 ? (
        <ul>
          {knownFacts.map((f, i) => (
            <li key={i}>
              <span className="badge badge-neutral">SCREENPLAY FACT</span> {f.text}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No direct screenplay quotes attached to this risk.</p>
      )}

      <h4 className="detail-h">What we don&apos;t know</h4>
      {unknowns.length > 0 || confidenceNote ? (
        <>
          {unknowns.length > 0 ? (
            <ul>
              {unknowns.map((u) => (
                <li key={u.slice(0, 48)}>
                  <span className="badge badge-neutral">UNKNOWN</span> {u}
                </li>
              ))}
            </ul>
          ) : null}
          {confidenceNote ? <p className="muted">{confidenceNote}</p> : null}
        </>
      ) : (
        <p className="muted">No open unknowns recorded for this analysis.</p>
      )}

      {risk.recommendation ? (
        <>
          <h4 className="detail-h">Recommended action</h4>
          <p>{risk.recommendation}</p>
        </>
      ) : null}
      {recs.length > 0 ? (
        <>
          <h4 className="detail-h">Linked actions</h4>
          <ul>
            {recs.map((rec) => (
              <li key={rec.id}>
                <strong>{rec.id}</strong> · {rec.title}
                {rec.expected_impact ? (
                  <span className="muted"> — expected impact: {rec.expected_impact}</span>
                ) : null}
              </li>
            ))}
          </ul>
          <h4 className="detail-h">Expected impact</h4>
          <p>
            {recs
              .map((rec) => rec.expected_impact)
              .filter(Boolean)
              .join(" ") || "Address the linked actions to reduce this risk."}
          </p>
        </>
      ) : null}

      {edges.length > 0 ? (
        <>
          <h4 className="detail-h">Dependencies</h4>
          <ul>
            {edges.map((e) => {
              const otherId = e.source_risk_id === risk.id ? e.target_risk_id : e.source_risk_id;
              const other = byId.get(otherId);
              const direction = e.source_risk_id === risk.id ? "→" : "←";
              return (
                <li key={e.id}>
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => onSelectRisk(otherId)}
                    title={other?.title ?? otherId}
                  >
                    {direction} {otherId} ({e.relationship})
                  </button>
                  {e.impact ? <span className="muted"> · {e.impact}</span> : null}
                </li>
              );
            })}
          </ul>
        </>
      ) : null}
    </div>
  );
}
