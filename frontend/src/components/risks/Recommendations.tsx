"use client";

import type { Recommendation } from "@/types";

export function RecommendationsList({
  recommendations,
  selected,
  disabled,
  onToggle,
}: {
  recommendations: Recommendation[];
  selected: string[];
  disabled?: boolean;
  onToggle: (id: string) => void;
}) {
  if (recommendations.length === 0) {
    return <p className="muted">No recommendations returned.</p>;
  }
  return (
    <ul className="rec-list">
      {recommendations.map((rec) => {
        const checked = selected.includes(rec.id);
        return (
          <li key={rec.id} className={`rec-item${checked ? " rec-checked" : ""}`}>
            <label>
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={() => onToggle(rec.id)}
                aria-label={`Select recommendation: ${rec.title}`}
              />
              <span>
                <span className="rec-title">{rec.title}</span>
                {rec.description ? <span className="rec-desc">{rec.description}</span> : null}
                <span className="rec-meta">
                  {rec.action_type} · priority {rec.priority}
                  {rec.addresses_risk_ids.length > 0
                    ? ` · addresses ${rec.addresses_risk_ids.join(", ")}`
                    : ""}
                </span>
                {rec.expected_impact ? (
                  <span className="rec-desc">{rec.expected_impact}</span>
                ) : null}
              </span>
            </label>
          </li>
        );
      })}
    </ul>
  );
}
