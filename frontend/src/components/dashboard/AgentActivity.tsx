"use client";

import type { AnalyzeResponse, RunEvent } from "@/types";

interface Step {
  label: string;
  done: boolean;
  active: boolean;
  note: string;
}

function shortTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour12: false });
}

interface CanonicalStep {
  label: string;
  match: string[];
}

/** Canonical autonomous workflow. Each step lights up only from real events. */
const WORKFLOW: CanonicalStep[] = [
  {
    label: "Analyzing screenplay",
    match: ["screenplay_received", "screenplay_parsed", "scenes_extracted"],
  },
  { label: "Identifying dependencies", match: ["dependencies_identified"] },
  {
    label: "Researching external facts",
    match: [
      "research_query_created",
      "parallel_search_started",
      "parallel_search_completed",
      "evidence_added",
      "research_errored",
    ],
  },
  {
    label: "Evaluating production risks",
    match: ["risk_analysis_started", "risks_detected", "dependency_graph_built"],
  },
  {
    label: "Calculating readiness",
    match: ["readiness_calculated", "recommendations_created", "run_completed"],
  },
];

/** Real persisted run events when available; otherwise the honest derived
 *  checklist (fixture / legacy payloads without an event log). */
export function AgentActivity({
  result,
  events,
  planning,
  planned,
}: {
  result: AnalyzeResponse;
  events?: RunEvent[];
  planning: boolean;
  planned: boolean;
}) {
  const log = events ?? [];
  if (log.length > 0) {
    const latestFor = (match: string[]) => [...log].reverse().find((e) => match.includes(e.type));
    return (
      <section className="card" aria-label="Agent activity">
        <h2 className="card-title">Agent activity</h2>
        <ol className="activity">
          {WORKFLOW.map((step) => {
            const latest = latestFor(step.match);
            const done = !!latest;
            return (
              <li key={step.label} className={done ? "done" : "todo"}>
                <span aria-hidden="true">{done ? "✓" : "○"}</span>
                <span>
                  <strong>{step.label}</strong>
                  <span className="muted">
                    {" "}
                    · {latest ? `${latest.message} · ${shortTime(latest.ts)}` : "pending"}
                  </span>
                </span>
              </li>
            );
          })}
          <li key="__plan" className={planned ? "done" : planning ? "active" : "todo"}>
            <span aria-hidden="true">{planned ? "✓" : planning ? "→" : "○"}</span>
            <span>
              <strong>Building mitigation plan</strong>
              <span className="muted">
                {" "}
                ·{" "}
                {planned
                  ? "Projected score calculated"
                  : planning
                    ? "Calling plan endpoint…"
                    : "Awaiting selection"}
              </span>
            </span>
          </li>
        </ol>
      </section>
    );
  }
  const research = result.research ?? [];
  const researchDone = research.length > 0;
  const researchLive = research.some((r) => r.status === "complete");
  const steps: Step[] = [
    {
      label: "Analyzing screenplay",
      done: true,
      active: false,
      note:
        result.analysis_source === "gemini"
          ? `Gemini extraction${result.extraction_model ? ` · ${result.extraction_model}` : ""}`
          : result.analysis_source === "fixture"
            ? "Sample data — no analysis ran"
            : "Local heuristic extraction",
    },
    {
      label: "Identifying dependencies",
      done: true,
      active: false,
      note: `${result.analysis.production_dependencies.length} production dependencies`,
    },
    {
      label: "Researching external facts",
      done: researchDone,
      active: false,
      note: researchDone
        ? researchLive
          ? `${research.filter((r) => r.status === "complete").length}/${research.length} Parallel queries returned sources`
          : "Queries ran — no usable sources returned"
        : "Not run — no research key configured",
    },
    {
      label: "Evaluating production risks",
      done: true,
      active: false,
      note: `${result.risks.length} risks classified with evidence levels`,
    },
    {
      label: "Calculating readiness",
      done: true,
      active: false,
      note: "Deterministic backend scoring",
    },
    {
      label: "Building mitigation plan",
      done: planned,
      active: planning,
      note: planned
        ? "Projected score calculated"
        : planning
          ? "Calling plan endpoint…"
          : "Awaiting selection",
    },
  ];
  return (
    <section className="card" aria-label="Agent activity">
      <h2 className="card-title">Agent activity</h2>
      <ol className="activity">
        {steps.map((s) => (
          <li key={s.label} className={s.done ? "done" : s.active ? "active" : "todo"}>
            <span aria-hidden="true">{s.done ? "✓" : s.active ? "→" : "○"}</span>
            <span>
              <strong>{s.label}</strong>
              <span className="muted"> · {s.note}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
