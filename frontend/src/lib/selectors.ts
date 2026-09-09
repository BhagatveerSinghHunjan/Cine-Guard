import type { AnalyzeResponse, Risk, Scene, Severity } from "@/types";

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];

const SEVERITY_RANK: Record<Severity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

export function riskScenes(risk: Risk): number[] {
  const scenes = new Set<number>(risk.affected_scenes ?? []);
  if (typeof risk.scene_number === "number") scenes.add(risk.scene_number);
  return [...scenes].sort((a, b) => a - b);
}

/** Heading of the risk's primary scene, for card hierarchy. */
export function riskSceneHeading(risk: Risk, scenes: Scene[]): string | null {
  const nums = riskScenes(risk);
  if (nums.length === 0) return null;
  const scene = scenes.find((s) => s.scene_number === nums[0]);
  return scene?.heading || null;
}

/** All risks touching a scene (via scene_number or affected_scenes). */
export function risksForScene(risks: Risk[], sceneNumber: number): Risk[] {
  return risks.filter((r) => riskScenes(r).includes(sceneNumber));
}

/** Worst open-risk severity for a scene, or null when no known risk. */
export function sceneRiskLevel(risks: Risk[], sceneNumber: number): Severity | null {
  let worst: Severity | null = null;
  for (const r of risksForScene(risks, sceneNumber)) {
    if (r.status === "mitigated") continue;
    if (worst === null || SEVERITY_RANK[r.severity] > SEVERITY_RANK[worst]) {
      worst = r.severity;
    }
  }
  return worst;
}

export function groupRisksBySeverity(risks: Risk[]): Record<Severity, Risk[]> {
  const groups: Record<Severity, Risk[]> = { critical: [], high: [], medium: [], low: [] };
  for (const r of risks) groups[r.severity]?.push(r);
  return groups;
}

export function recommendationsForRisk(
  recommendations: AnalyzeResponse["recommendations"],
  riskId: string,
) {
  return (recommendations ?? []).filter((rec) => rec.addresses_risk_ids.includes(riskId));
}

export function dependenciesForRisk(dependencies: AnalyzeResponse["dependencies"], riskId: string) {
  return (dependencies ?? []).filter(
    (d) => d.source_risk_id === riskId || d.target_risk_id === riskId,
  );
}

/** Risks impacted by one research result: any research-kind evidence item
 *  whose source URL appears in the result, or whose query matches the topic. */
export function risksForResearchEvidence(
  risks: Risk[],
  evidence: { topic: string; query?: string; sources?: { url?: string }[] },
): Risk[] {
  const urls = new Set((evidence.sources ?? []).map((s) => s.url).filter(Boolean));
  const topic = (evidence.topic ?? "").toLowerCase();
  const query = (evidence.query ?? "").toLowerCase();
  return risks.filter((r) =>
    (r.evidence_items ?? []).some((e) => {
      if (e.kind !== "research") return false;
      if (e.source_url && urls.has(e.source_url)) return true;
      const text = `${e.query ?? ""} ${e.text ?? ""}`.toLowerCase();
      return (topic && text.includes(topic)) || (query && e.query?.toLowerCase() === query);
    }),
  );
}

/** Deterministic one-line executive explanation derived from live counts. */
export function readinessExplanation(result: AnalyzeResponse): string {
  const c = result.risk_counts ?? {};
  const critical = c["critical"] ?? 0;
  const high = c["high"] ?? 0;
  const medium = c["medium"] ?? 0;
  const total = result.risks.length;
  if (total === 0) return "No production risks flagged. The shoot looks clear on current evidence.";
  if (critical > 0)
    return `Production is currently blocked by ${critical} critical dependenc${critical === 1 ? "y" : "ies"}. Resolve ${critical === 1 ? "it" : "them"} before locking the schedule.`;
  if (high > 0)
    return `Production is at risk from ${high} high-severity issue${high === 1 ? "" : "s"}. Mitigate ${high === 1 ? "it" : "them"} to reach READY.`;
  if (medium > 0)
    return `${medium} medium-severity item${medium === 1 ? " needs" : "s need"} planning attention, but nothing blocks the shoot.`;
  return "Only low-severity watch items remain.";
}

export interface ScheduleRow {
  day: number;
  scenes: number[];
  location: string;
  keyDependencies: string[];
  notes: string[];
}

/** Derived shooting order: consecutive same-location scenes share a day. */
export function deriveSchedule(scenes: Scene[]): ScheduleRow[] {
  const rows: ScheduleRow[] = [];
  for (const scene of [...scenes].sort((a, b) => a.scene_number - b.scene_number)) {
    const last = rows[rows.length - 1];
    if (last && last.location === (scene.location || "Unspecified")) {
      last.scenes.push(scene.scene_number);
      for (const dep of scene.production_requirements ?? []) {
        if (!last.keyDependencies.includes(dep)) last.keyDependencies.push(dep);
      }
    } else {
      rows.push({
        day: rows.length + 1,
        scenes: [scene.scene_number],
        location: scene.location || "Unspecified",
        keyDependencies: [...(scene.production_requirements ?? [])],
        notes: [],
      });
    }
  }
  return rows;
}
