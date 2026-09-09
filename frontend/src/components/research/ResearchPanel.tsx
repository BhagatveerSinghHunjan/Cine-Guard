"use client";

import { risksForResearchEvidence } from "@/lib/selectors";
import type { AnalyzeResponse } from "@/types";

export function ResearchPanel({
  result,
  onSelectRisk,
}: {
  result: AnalyzeResponse;
  onSelectRisk?: (id: string) => void;
}) {
  const research = result.research ?? [];
  return (
    <div>
      {(result.extraction_warnings ?? []).length > 0 ? (
        <p className="muted">{result.extraction_warnings?.join(" ")}</p>
      ) : null}
      {research.length === 0 ? (
        <section className="card" aria-label="Research unavailable">
          <h2 className="card-title">Research unavailable</h2>
          <p className="muted">
            External research did not run for this analysis. Configure PARALLEL_API_KEY on the
            backend to enable live Parallel Search evidence.
          </p>
          {result.research_notes.length > 0 ? (
            <ul>
              {result.research_notes.map((n) => (
                <li key={n.slice(0, 40)} className="muted">
                  {n}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : (
        <>
          <p className="muted">
            Research Evidence — live external research via Parallel Search. Each query flows from
            search to evidence to the risks it informs.
          </p>
          <ul className="risk-list">
            {research.map((ev) => {
              const impacted = risksForResearchEvidence(result.risks, ev);
              return (
                <li key={ev.topic} className="risk-card">
                  <div className="risk-top">
                    <span className="badge badge-neutral">Parallel</span>
                    <span className="badge badge-neutral">{ev.status}</span>
                  </div>
                  <h3 className="risk-title">{ev.topic}</h3>
                  <p className="muted research-flow">Parallel Search → Evidence → Risk Impact</p>
                  {ev.summary ? <p className="risk-desc">{ev.summary}</p> : null}
                  <p className="muted">
                    Provider: {ev.provider ?? "parallel"}
                    {ev.retrieved_at ? ` · retrieved ${ev.retrieved_at.slice(0, 10)}` : ""}
                    {ev.query ? ` · query: ${ev.query}` : ""}
                  </p>
                  {ev.status === "error" ? (
                    <p className="muted">
                      Research unavailable for this query — the provider returned an error. No
                      sources were recorded.
                    </p>
                  ) : null}
                  {ev.status === "empty" ? (
                    <p className="muted">
                      No evidence found — the search ran but returned no usable sources. This is
                      recorded as unknown, not as a confirmed fact either way.
                    </p>
                  ) : null}
                  {(ev.sources ?? []).map((s) => (
                    <div key={s.url} className="evidence-item">
                      <p>
                        <strong>{s.title || s.domain || "Untitled source"}</strong>
                        {s.domain ? ` · ${s.domain}` : ""}
                      </p>
                      {s.excerpt ? <p className="risk-desc">{s.excerpt}</p> : null}
                      {s.url ? (
                        <p className="evidence-source">
                          <a href={s.url} target="_blank" rel="noreferrer">
                            {s.url}
                          </a>
                        </p>
                      ) : null}
                    </div>
                  ))}
                  <h4 className="detail-h">Risk impact</h4>
                  {impacted.length > 0 ? (
                    <ul>
                      {impacted.map((r) => (
                        <li key={r.id}>
                          {onSelectRisk ? (
                            <button
                              type="button"
                              className="link-btn"
                              onClick={() => onSelectRisk(r.id)}
                            >
                              {r.id} · {r.severity} · {r.title}
                            </button>
                          ) : (
                            <span>
                              {r.id} · {r.severity} · {r.title}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">No risks cite this evidence yet.</p>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
