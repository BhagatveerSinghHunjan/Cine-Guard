"use client";

import type { EvidenceItem } from "@/types";

const KIND_LABEL: Record<string, string> = {
  screenplay: "SCREENPLAY FACT",
  research: "RESEARCHED FACT",
  inference: "INFERENCE",
  unknown: "UNKNOWN",
};

export function EvidenceList({ items, fallback }: { items: EvidenceItem[]; fallback?: string }) {
  if (items.length === 0) {
    if (!fallback) return null;
    return (
      <div className="evidence">
        <p className="evidence-title">Evidence</p>
        <div className="evidence-item">
          <span className="badge badge-neutral">SCREENPLAY</span>
          <p>{fallback}</p>
        </div>
      </div>
    );
  }
  return (
    <div className="evidence">
      <p className="evidence-title">Evidence</p>
      <ul>
        {items.map((e, i) => (
          <li key={i} className="evidence-item">
            <span className="badge badge-neutral">{KIND_LABEL[e.kind] ?? e.kind}</span>
            <p>{e.text}</p>
            {e.kind === "research" && (e.source_title || e.source_url) ? (
              <p className="evidence-source">
                {e.source_title ? <strong>{e.source_title}</strong> : null}
                {e.source_domain ? ` · ${e.source_domain}` : null}{" "}
                {e.provider ? ` · via ${e.provider}` : null}{" "}
                {e.source_url ? (
                  <a href={e.source_url} target="_blank" rel="noreferrer">
                    {e.source_url}
                  </a>
                ) : null}
                {e.retrieved_at ? (
                  <span className="muted"> · retrieved {e.retrieved_at.slice(0, 10)}</span>
                ) : null}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
