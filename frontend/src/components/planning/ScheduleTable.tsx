"use client";

import { riskScenes } from "@/lib/selectors";
import type { AnalyzeResponse, FixPlan } from "@/types";

/**
 * Revised production plan, built only from backend state: each mitigation
 * action becomes rows showing the original condition, the problem, the
 * recommended change, the new condition, and the measured risk reduction.
 */
export function ScheduleTable({ result, plan }: { result: AnalyzeResponse; plan: FixPlan | null }) {
  const byRiskId = new Map(result.risks.map((r) => [r.id, r]));
  const byScene = new Map(result.analysis.scenes.map((s) => [s.scene_number, s]));
  const actions = plan?.actions ?? [];
  const highResolved = new Set<string>();
  for (const a of actions) {
    for (const rid of a.affected_risk_ids) {
      const r = byRiskId.get(rid);
      if (r && (r.severity === "high" || r.severity === "critical")) highResolved.add(rid);
    }
  }

  if (actions.length === 0) return <p className="muted">No mitigations applied yet.</p>;
  return (
    <div className="schedule-wrap">
      <dl className="snapshot">
        <div>
          <dt>Production blockers remaining</dt>
          <dd>{plan?.remaining_blockers.length ?? 0}</dd>
        </div>
        <div>
          <dt>High-risk dependencies resolved</dt>
          <dd>{highResolved.size}</dd>
        </div>
        <div>
          <dt>Risks mitigated</dt>
          <dd>{plan?.affected_risk_ids.length ?? 0}</dd>
        </div>
      </dl>
      {plan?.schedule_impact ? (
        <p className="muted">Estimated schedule impact: {plan.schedule_impact}</p>
      ) : null}
      <div className="table-scroll">
        <table className="schedule">
          <thead>
            <tr>
              <th scope="col">Scene</th>
              <th scope="col">Original condition</th>
              <th scope="col">Problem</th>
              <th scope="col">Recommended change</th>
              <th scope="col">New condition</th>
              <th scope="col">Risk reduction</th>
              <th scope="col">Schedule impact</th>
            </tr>
          </thead>
          <tbody>
            {actions.flatMap((a) => {
              const scenes = a.affected_scenes.length > 0 ? a.affected_scenes : [0];
              return scenes.map((n, i) => {
                const scene = byScene.get(n);
                const problems = a.affected_risk_ids
                  .map((rid) => byRiskId.get(rid))
                  .filter((r) => r && (riskScenes(r).includes(n) || n === 0));
                return (
                  <tr key={`${a.id}-${n}`} className="row-changed">
                    <td>{n > 0 ? `Scene ${n}` : "Global"}</td>
                    <td>
                      {scene
                        ? `${scene.heading || "Untitled scene"}${scene.location ? ` · ${scene.location}` : ""}`
                        : "Production-wide"}
                    </td>
                    <td>
                      {problems.length > 0
                        ? problems.map((r) => `${r!.id} (${r!.severity}): ${r!.title}`).join("; ")
                        : "—"}
                    </td>
                    <td>{i === 0 ? a.title : "↳ same mitigation"}</td>
                    <td>Mitigated — verify on the day</td>
                    <td>{i === 0 ? `−${a.expected_risk_reduction.toFixed(1)} pts` : "—"}</td>
                    <td>{i === 0 ? a.schedule_impact || "—" : "—"}</td>
                  </tr>
                );
              });
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
