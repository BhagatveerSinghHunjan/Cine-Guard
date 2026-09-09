"use client";

import { InitialConcernsList } from "@/components/analysis/InitialConcerns";
import { AgentActivity } from "@/components/dashboard/AgentActivity";
import { ReadinessScore } from "@/components/dashboard/ReadinessScore";
import { TrustIndicator } from "@/components/dashboard/TrustIndicator";
import { DependencyGrid } from "@/components/dependencies/DependencyGrid";
import { FixPlanSection } from "@/components/planning/FixPlanSection";
import { RiskList, RiskSummary } from "@/components/risks/Risks";
import { Alert } from "@/components/ui/Alert";
import { readinessExplanation, riskScenes } from "@/lib/selectors";
import type { AnalyzeResponse, FixPlan, RunEvent } from "@/types";

export function Overview({
  result,
  events,
  planning,
  setPlanning,
  planned,
  plan,
  setPlan,
  selected,
  onToggleSelect,
  onSelectRisk,
}: {
  result: AnalyzeResponse;
  events: RunEvent[];
  planning: boolean;
  setPlanning: (v: boolean) => void;
  planned: boolean;
  plan: FixPlan | null;
  setPlan: (plan: FixPlan | null) => void;
  selected: string[];
  onToggleSelect: (id: string) => void;
  onSelectRisk: (id: string) => void;
}) {
  const concerns = result.analysis.initial_concerns ?? [];
  const topRisks = result.risks.slice(0, 3);
  const blockers = result.readiness?.blockers ?? [];
  const research = result.research ?? [];
  const sourcesFound = research.reduce((n, r) => n + (r.sources?.length ?? 0), 0);
  const affectedScenes = new Set<number>();
  for (const r of result.risks) for (const n of riskScenes(r)) affectedScenes.add(n);
  return (
    <div className="overview">
      <div className="overview-head">
        <div>
          <p className="eyebrow">{result.project_title}</p>
          <h2 tabIndex={-1} id="results-heading">
            Production readiness
          </h2>
        </div>
      </div>

      <div className="readiness-row">
        <ReadinessScore
          score={result.readiness_score}
          status={result.readiness?.status}
          methodology={result.readiness?.methodology}
          breakdown={result.readiness?.penalty_breakdown}
        />
        <RiskSummary counts={result.risk_counts} />
      </div>
      <p className="exec-line" role="status">
        {readinessExplanation(result)}
      </p>

      <dl className="hero-strip" aria-label="Production situation at a glance">
        <div>
          <dt>Production blockers</dt>
          <dd>{blockers.length > 0 ? blockers.join(", ") : "None"}</dd>
        </div>
        <div>
          <dt>Research findings</dt>
          <dd>
            {research.length > 0
              ? `${research.filter((r) => r.status === "complete").length}/${research.length} queries · ${sourcesFound} sources`
              : "No external research"}
          </dd>
        </div>
        <div>
          <dt>Affected scenes</dt>
          <dd>
            {affectedScenes.size > 0
              ? [...affectedScenes].sort((a, b) => a - b).join(", ")
              : "None"}
          </dd>
        </div>
      </dl>

      <div className="grid-2">
        <AgentActivity result={result} events={events} planning={planning} planned={planned} />
        <TrustIndicator result={result} />
      </div>

      <section className="card" aria-label="Production snapshot">
        <h2 className="card-title">Production snapshot</h2>
        <dl className="snapshot">
          <div>
            <dt>Scenes</dt>
            <dd>{result.analysis.scenes.length}</dd>
          </div>
          <div>
            <dt>Characters</dt>
            <dd>{result.analysis.characters.length}</dd>
          </div>
          <div>
            <dt>Locations</dt>
            <dd>{result.analysis.locations.length}</dd>
          </div>
          <div>
            <dt>Dependencies</dt>
            <dd>{result.analysis.production_dependencies.length}</dd>
          </div>
        </dl>
        <p className="muted">
          {result.analysis.genre ? `${result.analysis.genre} · ` : ""}
          {result.analysis.estimated_complexity &&
          result.analysis.estimated_complexity !== "unknown"
            ? `${result.analysis.estimated_complexity} complexity · `
            : ""}
          {result.analysis_source === "gemini"
            ? `Gemini extraction${result.extraction_model ? ` · ${result.extraction_model}` : ""}`
            : result.analysis_source === "fixture"
              ? "Sample data"
              : "Local heuristic extraction"}
        </p>
      </section>

      {(result.extraction_warnings ?? []).length > 0 ? (
        <Alert variant="info" title="Extraction note">
          {(result.extraction_warnings ?? []).map((w) => (
            <p key={w.slice(0, 40)} className="research-note">
              {w}
            </p>
          ))}
        </Alert>
      ) : null}

      <h3 className="section-h">Top risks</h3>
      <RiskList risks={topRisks} scenes={result.analysis.scenes} onSelect={onSelectRisk} />

      <FixPlanSection
        result={result}
        selected={selected}
        onToggle={onToggleSelect}
        plan={plan}
        setPlan={setPlan}
        planning={planning}
        setPlanning={setPlanning}
      />

      <h3 className="section-h">Extracted concerns ({concerns.length})</h3>
      <InitialConcernsList concerns={concerns} />

      <h3 className="section-h">Production dependencies</h3>
      <DependencyGrid analysis={result.analysis} />
    </div>
  );
}
