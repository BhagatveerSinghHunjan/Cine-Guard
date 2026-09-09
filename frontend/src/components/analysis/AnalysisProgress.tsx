"use client";

import { ANALYSIS_STAGES } from "@/lib/stages";

export function AnalysisProgress({ activeIndex }: { activeIndex: number }) {
  return (
    <div aria-live="polite" aria-label="Analysis progress">
      <ol className="stages">
        {ANALYSIS_STAGES.map((stage, i) => {
          const state = i < activeIndex ? "done" : i === activeIndex ? "active" : "todo";
          const glyph = state === "done" ? "✓" : state === "active" ? "→" : "○";
          return (
            <li key={stage.id} className={`stage stage-${state}`}>
              <span className="stage-glyph" aria-hidden="true">
                {glyph}
              </span>
              <span>
                <span className="stage-label">
                  {stage.label}
                  <span className="sr-only">
                    {state === "done" ? " (done)" : state === "active" ? " (in progress)" : ""}
                  </span>
                </span>
                <span className="stage-hint">{stage.hint}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
