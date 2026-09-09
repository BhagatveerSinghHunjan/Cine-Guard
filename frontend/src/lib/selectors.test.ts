import { describe, expect, it } from "vitest";
import {
  deriveSchedule,
  readinessExplanation,
  risksForScene,
  sceneRiskLevel,
} from "@/lib/selectors";
import type { AnalyzeResponse, Risk, Scene } from "@/types";

function risk(
  id: string,
  severity: "critical" | "high" | "medium" | "low",
  scenes: number[],
): Risk {
  return {
    id,
    affected_scenes: scenes,
    category: "stunt",
    severity,
    title: id,
    description: "d",
  };
}

describe("selectors", () => {
  it("maps risks to scenes and picks the worst open level", () => {
    const risks = [risk("R-1", "medium", [2]), risk("R-2", "high", [2, 3])];
    expect(risksForScene(risks, 2).map((r) => r.id)).toEqual(["R-1", "R-2"]);
    expect(sceneRiskLevel(risks, 2)).toBe("high");
    expect(sceneRiskLevel(risks, 3)).toBe("high");
    expect(sceneRiskLevel(risks, 9)).toBeNull();
  });

  it("ignores mitigated risks for scene level", () => {
    const risks = [{ ...risk("R-1", "critical", [1]), status: "mitigated" as const }];
    expect(sceneRiskLevel(risks, 1)).toBeNull();
  });

  it("explains readiness deterministically from counts", () => {
    const base = { risks: [], risk_counts: {} } as unknown as AnalyzeResponse;
    expect(readinessExplanation(base)).toMatch(/no production risks/i);
    expect(
      readinessExplanation({
        ...base,
        risks: [{ ...risk("R-1", "critical", []) }],
        risk_counts: { critical: 3 },
      }),
    ).toMatch(/blocked by 3 critical/);
    expect(
      readinessExplanation({
        ...base,
        risks: [{ ...risk("R-1", "high", []) }],
        risk_counts: { critical: 0, high: 2 },
      }),
    ).toMatch(/at risk from 2 high/);
  });

  it("derives shooting days by grouping consecutive locations", () => {
    const scenes: Scene[] = [
      {
        scene_number: 1,
        heading: "A",
        location: "Pier",
        time_of_day: "",
        characters: [],
        description: "",
        production_requirements: ["boat"],
      },
      {
        scene_number: 2,
        heading: "B",
        location: "Pier",
        time_of_day: "",
        characters: [],
        description: "",
        production_requirements: ["rain"],
      },
      {
        scene_number: 3,
        heading: "C",
        location: "Roof",
        time_of_day: "",
        characters: [],
        description: "",
        production_requirements: [],
      },
    ];
    const rows = deriveSchedule(scenes);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ day: 1, scenes: [1, 2], location: "Pier" });
    expect(rows[0].keyDependencies).toEqual(["boat", "rain"]);
    expect(rows[1]).toMatchObject({ day: 2, scenes: [3] });
  });
});
