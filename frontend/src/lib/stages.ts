export type StageId = "reading" | "extracting" | "researching" | "reasoning" | "scoring";

export interface Stage {
  id: StageId;
  label: string;
  hint: string;
}

export const ANALYSIS_STAGES: Stage[] = [
  { id: "reading", label: "Reading screenplay", hint: "Loading file in your browser" },
  { id: "extracting", label: "Extracting scenes", hint: "Backend parses structure" },
  {
    id: "researching",
    label: "Researching constraints",
    hint: "Backend checks external evidence",
  },
  {
    id: "reasoning",
    label: "Reasoning production risks",
    hint: "Evidence-aware risk classification",
  },
  {
    id: "scoring",
    label: "Computing readiness",
    hint: "Deterministic scoring + recommendations",
  },
];

/** Map the backend's persisted run stage to a visible step index.
 *  queued/analyzing_screenplay cover local read + extraction (0–1),
 *  then one step per real backend stage. Terminal states resolve fully. */
export function stageIndexForRun(status?: string, currentStage?: string): number {
  if (status === "completed") return ANALYSIS_STAGES.length;
  if (status === "failed") return ANALYSIS_STAGES.length;
  switch (currentStage) {
    case "researching":
      return 2;
    case "reasoning_risks":
      return 3;
    case "building_plan":
      return 4;
    case "analyzing_screenplay":
    case "queued":
    default:
      return 1;
  }
}
