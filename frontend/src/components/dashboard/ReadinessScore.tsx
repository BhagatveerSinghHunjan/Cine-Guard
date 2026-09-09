"use client";

import { useState } from "react";
import { useCountUp } from "@/lib/useCountUp";
import type { ProductionReadiness } from "@/types";

function tone(score: number): string {
  if (score >= 85) return "tone-good";
  if (score >= 65) return "tone-warn";
  return "tone-bad";
}

export function ReadinessScore({
  score,
  status,
  methodology,
  breakdown,
  compact,
}: {
  score: number;
  status?: string;
  methodology?: string;
  breakdown?: ProductionReadiness["penalty_breakdown"];
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const animated = useCountUp(score);
  const lines = breakdown ?? [];
  const canExpand = lines.length > 0 || !!methodology;
  return (
    <div className={`readiness ${tone(score)}${compact ? " readiness-compact" : ""}`}>
      <button
        type="button"
        className="readiness-toggle"
        onClick={() => canExpand && setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`Production readiness ${score.toFixed(1)} percent${status ? `, ${status}` : ""}. ${canExpand ? (open ? "Hide" : "Show") + " score breakdown." : ""}`}
        disabled={!canExpand}
      >
        <span className="readiness-value">{animated.toFixed(1)}%</span>
        <span className="readiness-label">
          Production Readiness{status ? ` · ${status}` : ""}
          {canExpand ? <span className="muted"> · {open ? "hide" : "why?"} ▾</span> : null}
        </span>
      </button>
      {open && lines.length > 0 ? (
        <dl className="breakdown">
          <div className="breakdown-row breakdown-base">
            <dt>Base readiness</dt>
            <dd>100.0</dd>
          </div>
          {lines.map((line) => (
            <div key={line.severity} className="breakdown-row">
              <dt>
                {line.severity} × {line.count}
                <span className="muted"> (weight {line.weight})</span>
              </dt>
              <dd>−{line.penalty.toFixed(1)}</dd>
            </div>
          ))}
          <div className="breakdown-row breakdown-total">
            <dt>Readiness</dt>
            <dd>{score.toFixed(1)}</dd>
          </div>
        </dl>
      ) : null}
      {open && methodology ? <p className="muted methodology">{methodology}</p> : null}
      {methodology && !compact && !open ? <p className="muted methodology">{methodology}</p> : null}
    </div>
  );
}

export function ReadinessStatusBadge({ readiness }: { readiness?: ProductionReadiness }) {
  if (!readiness) return null;
  return (
    <span
      className={`badge status-${readiness.status.replace(/ /g, "-")}`}
      title="Readiness status"
    >
      {readiness.status}
    </span>
  );
}
