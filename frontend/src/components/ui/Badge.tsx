import type { Severity } from "@/types";

const LABELS: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`badge badge-${severity}`} aria-label={`${LABELS[severity]} severity`}>
      {LABELS[severity]}
    </span>
  );
}

export function CategoryBadge({ category }: { category: string }) {
  return <span className="badge badge-neutral">{category}</span>;
}
