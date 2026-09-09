"use client";

import { useState } from "react";
import { RecommendationsList } from "@/components/risks/Recommendations";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ReadinessScore } from "@/components/dashboard/ReadinessScore";
import { api, friendlyErrorMessage } from "@/lib/api";
import type { AnalyzeResponse, FixPlan } from "@/types";

export function FixPlanSection({
  result,
  selected,
  onToggle,
  plan,
  setPlan,
  planning,
  setPlanning,
}: {
  result: AnalyzeResponse;
  selected: string[];
  onToggle: (id: string) => void;
  plan: FixPlan | null;
  setPlan: (plan: FixPlan | null) => void;
  planning: boolean;
  setPlanning: (v: boolean) => void;
}) {
  const recommendations = result.recommendations ?? [];
  const [planError, setPlanError] = useState<string | null>(null);

  async function buildPlan() {
    if (!result.run_id || selected.length === 0 || planning) return;
    setPlanning(true);
    setPlanError(null);
    try {
      const res = await api.postPlan(result.run_id, selected);
      setPlan(res.fix_plan ?? null);
    } catch (err) {
      setPlanError(friendlyErrorMessage(err));
    } finally {
      setPlanning(false);
    }
  }

  return (
    <div>
      <h3 className="section-h">Fix production plan</h3>
      <p className="muted">
        Select mitigations to apply. Projected readiness is calculated by the backend — never
        estimated in the browser.
      </p>
      <h4 className="detail-h">Recommendations ({recommendations.length})</h4>
      <RecommendationsList
        recommendations={recommendations}
        selected={selected}
        disabled={planning || !result.run_id}
        onToggle={onToggle}
      />
      <div className="plan-actions">
        <Button
          variant="primary"
          disabled={selected.length === 0 || planning || !result.run_id}
          loading={planning}
          onClick={buildPlan}
          title={!result.run_id ? "Run state unavailable" : undefined}
        >
          Build Revised Production Plan{selected.length > 0 ? ` (${selected.length})` : ""}
        </Button>
        {!result.run_id ? (
          <p className="muted cta-note">Run state unavailable — re-run analysis.</p>
        ) : null}
        {planError ? (
          <Alert variant="error" title="Fix plan failed">
            <p>{planError}</p>
            <Button variant="ghost" onClick={buildPlan} disabled={selected.length === 0}>
              Retry
            </Button>
          </Alert>
        ) : null}
      </div>

      {planning ? (
        <section className="card" aria-live="polite" aria-label="Building mitigation plan">
          <h2 className="card-title">Building mitigation plan…</h2>
          <p className="muted">Applying {selected.length} recommendation(s) and re-scoring.</p>
        </section>
      ) : null}

      {plan ? (
        <>
          <h3 className="section-h">Before / after</h3>
          <div className="before-after">
            <div>
              <p className="eyebrow">Current</p>
              <ReadinessScore
                score={result.readiness_score}
                status={result.readiness?.status}
                compact
              />
            </div>
            <p className="before-after-arrow" aria-hidden="true">
              ↓
            </p>
            <div>
              <p className="eyebrow">After mitigation</p>
              <ReadinessScore
                score={plan.projected_readiness.score}
                status={plan.projected_readiness.status}
                compact
              />
            </div>
          </div>
          <dl className="snapshot">
            <div>
              <dt>Risks mitigated</dt>
              <dd>{plan.affected_risk_ids.length}</dd>
            </div>
            <div>
              <dt>Remaining blockers</dt>
              <dd>
                {plan.remaining_blockers.length > 0 ? plan.remaining_blockers.join(", ") : "None"}
              </dd>
            </div>
          </dl>
          {plan.schedule_impact ? <p className="muted">{plan.schedule_impact}</p> : null}

          <h3 className="section-h">Recommended actions ({plan.actions.length})</h3>
          <ul className="risk-list">
            {plan.actions.map((a) => (
              <li key={a.id} className="risk-card">
                <div className="risk-top">
                  <span className="badge badge-neutral">{a.id}</span>
                  <span className="risk-scene">
                    {a.affected_scenes.length > 0
                      ? `Scenes ${a.affected_scenes.join(", ")}`
                      : "Global"}
                  </span>
                </div>
                <h3 className="risk-title">{a.title}</h3>
                {a.description ? <p className="risk-desc">{a.description}</p> : null}
                <p className="risk-rec">
                  <strong>Mitigates:</strong> {a.affected_risk_ids.join(", ")} (−
                  {a.expected_risk_reduction.toFixed(1)} pts)
                </p>
                {a.schedule_impact ? (
                  <p className="risk-rec">
                    <strong>Schedule:</strong> {a.schedule_impact}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
