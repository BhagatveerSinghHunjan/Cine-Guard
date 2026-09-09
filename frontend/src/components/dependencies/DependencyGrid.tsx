"use client";

import type { ScreenplayAnalysis } from "@/types";

const GROUPS: Array<{ key: keyof ScreenplayAnalysis; label: string }> = [
  { key: "locations", label: "Locations" },
  { key: "characters", label: "Cast" },
  { key: "props", label: "Props" },
  { key: "vehicles", label: "Vehicles" },
  { key: "music", label: "Music" },
  { key: "stunts", label: "Stunts" },
  { key: "vfx_requirements", label: "VFX" },
  { key: "weather_dependencies", label: "Weather" },
  { key: "special_equipment", label: "Special equipment" },
  { key: "permits_or_clearances", label: "Permits" },
];

export function DependencyGrid({ analysis }: { analysis: ScreenplayAnalysis }) {
  return (
    <div className="dep-grid">
      {GROUPS.map((g) => {
        const values = (analysis[g.key] as string[] | undefined) ?? [];
        return (
          <div key={g.key} className="dep-group">
            <h3>
              {g.label} <span className="dep-count">{values.length}</span>
            </h3>
            {values.length === 0 ? (
              <p className="muted">—</p>
            ) : (
              <ul>
                {values.slice(0, 12).map((v) => (
                  <li key={v}>{v}</li>
                ))}
                {values.length > 12 ? <li className="muted">+{values.length - 12} more</li> : null}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
