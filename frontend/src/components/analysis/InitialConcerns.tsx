"use client";

import type { InitialConcern } from "@/types";

function sceneLabel(c: InitialConcern): string {
  const nums = c.scene_numbers ?? [];
  if (nums.length === 0) return "Global";
  return nums.map((n) => `Scene ${n}`).join(", ");
}

export function InitialConcernsList({ concerns }: { concerns: InitialConcern[] }) {
  if (concerns.length === 0) {
    return <p className="muted">No direct production concerns extracted from the text.</p>;
  }
  return (
    <ul className="risk-list">
      {concerns.map((c, i) => (
        <li key={`${c.title}-${i}`}>
          <article className="risk-card" aria-label={`Production concern: ${c.title}`}>
            <div className="risk-top">
              <span className="badge badge-neutral">{c.category ?? "other"}</span>
              {c.evidence_level ? (
                <span className="badge badge-neutral">{c.evidence_level}</span>
              ) : null}
              <span className="risk-scene">{sceneLabel(c)}</span>
            </div>
            <h3 className="risk-title">{c.title}</h3>
            {c.description ? <p className="risk-desc">{c.description}</p> : null}
            {c.recommendation ? (
              <p className="risk-rec">
                <strong>Recommendation:</strong> {c.recommendation}
              </p>
            ) : null}
          </article>
        </li>
      ))}
    </ul>
  );
}
