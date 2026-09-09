import { describe, expect, it } from "vitest";
import { toGraphData } from "@/lib/graph";
import type { Risk, RiskDependency, Scene } from "@/types";

const scenes: Scene[] = [
  {
    scene_number: 18,
    heading: "EXT. ROOFTOP - NIGHT",
    location: "Rooftop",
    time_of_day: "Night",
    characters: ["Mara"],
    description: "d",
    production_requirements: ["helicopter"],
  },
  {
    scene_number: 19,
    heading: "INT. DINER - DAY",
    location: "Diner",
    time_of_day: "Day",
    characters: [],
    description: "d",
    production_requirements: [],
  },
];

const risks: Risk[] = [
  {
    id: "R-001",
    affected_scenes: [18],
    category: "permit",
    severity: "critical",
    title: "Rooftop access",
    description: "d",
  },
  {
    id: "R-002",
    scene_number: 19,
    category: "cast",
    severity: "low",
    title: "Availability unknown",
    description: "d",
  },
];

const deps: RiskDependency[] = [
  {
    id: "D-001",
    source_risk_id: "R-001",
    target_risk_id: "R-002",
    relationship: "blocks",
    impact: "Scene 18 holds up 19.",
  },
];

describe("toGraphData", () => {
  it("creates risk and referenced-scene nodes only", () => {
    const g = toGraphData(risks, deps, scenes);
    const ids = g.nodes.map((n) => n.id);
    expect(ids).toContain("risk:R-001");
    expect(ids).toContain("risk:R-002");
    expect(ids).toContain("scene:18");
    expect(ids).toContain("scene:19");
    expect(ids).toHaveLength(4);
  });

  it("emits risk→scene edges plus backend dependency edges", () => {
    const g = toGraphData(risks, deps, scenes);
    expect(g.edges).toContainEqual({
      id: "e-risk:R-001-scene:18",
      source: "risk:R-001",
      target: "scene:18",
      label: "affects",
    });
    expect(g.edges).toContainEqual({
      id: "e-D-001",
      source: "risk:R-001",
      target: "risk:R-002",
      label: "blocks",
    });
  });

  it("handles empty input without crashing", () => {
    expect(toGraphData([], [], [])).toEqual({ nodes: [], edges: [] });
  });
});
