"use client";

import { FixPlanSection } from "@/components/planning/FixPlanSection";
import { ScheduleTable } from "@/components/planning/ScheduleTable";
import type { AnalyzeResponse, FixPlan } from "@/types";

export function PlanWorkspace({
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
  return (
    <div>
      <section className="card plan-cta" aria-label="Fix production plan">
        <div>
          <h2 className="card-title">Fix production plan</h2>
          <p className="muted">
            Select the mitigations to apply. Projected readiness is calculated by the backend —
            never estimated in the browser.
          </p>
        </div>
        <span className="badge badge-neutral" aria-live="polite">
          {selected.length > 0 ? `${selected.length} selected` : "None selected"}
        </span>
      </section>

      <div id="plan-recs">
        <FixPlanSection
          result={result}
          selected={selected}
          onToggle={onToggle}
          plan={plan}
          setPlan={setPlan}
          planning={planning}
          setPlanning={setPlanning}
        />
      </div>

      {plan ? (
        <>
          <h3 className="section-h">Revised production plan</h3>
          {plan.revised_plan ? <p className="muted">{plan.revised_plan}</p> : null}
          <ScheduleTable result={result} plan={plan} />
        </>
      ) : null}
    </div>
  );
}
