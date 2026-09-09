"use client";

import type { AnalyzeResponse } from "@/types";

/** Compact trust summary from real backend counts only. */
export function TrustIndicator({ result }: { result: AnalyzeResponse }) {
  let screenplayFacts = 0;
  let researchedFacts = 0;
  let inferences = 0;
  for (const r of result.risks) {
    for (const e of r.evidence_items ?? []) {
      if (e.kind === "screenplay") screenplayFacts += 1;
      else if (e.kind === "research") researchedFacts += 1;
      else inferences += 1;
    }
  }
  const unknowns = result.analysis.unknowns?.length ?? 0;
  const withEvidence = result.risks.filter((r) => (r.evidence_items ?? []).length > 0).length;
  const coverage =
    result.risks.length > 0 ? Math.round((withEvidence / result.risks.length) * 100) : 100;
  return (
    <section className="card" aria-label="Evidence trust summary">
      <h2 className="card-title">Evidence coverage</h2>
      <p className="trust-value">{coverage}%</p>
      <p className="muted">
        Based on {screenplayFacts} screenplay fact{screenplayFacts === 1 ? "" : "s"},{" "}
        {researchedFacts} researched fact{researchedFacts === 1 ? "" : "s"}, {inferences} inference
        {inferences === 1 ? "" : "s"} and {unknowns} unknown
        {unknowns === 1 ? "" : "s"}.
      </p>
    </section>
  );
}
