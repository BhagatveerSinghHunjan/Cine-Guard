"""Production-plan builder — transparent scoring, nothing hardcoded.

Formula: start at 100, deduct critical*15 + high*5 + medium*2 + low*0.5,
clamp to [0, 100]. The score is always derived from the actual risk
list, so demos show real movement instead of a canned '61%'.
"""

from app.models.schemas import ProductionPlan, Risk, ScreenplayAnalysis
from app.tools.risk_tools import count_by_severity


def compute_readiness(risks: list[Risk]) -> float:
    counts = count_by_severity(risks or [])
    score = 100.0 - (
        counts.get("critical", 0) * 15.0
        + counts.get("high", 0) * 5.0
        + counts.get("medium", 0) * 2.0
        + counts.get("low", 0) * 0.5
    )
    return round(max(0.0, min(100.0, score)), 1)


def build_plan(
    analysis: ScreenplayAnalysis | None, risks: list[Risk]
) -> ProductionPlan:
    risks = risks or []
    counts = count_by_severity(risks)

    top = sorted(
        risks,
        key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}[r.severity.value],
    )[:5]
    recommendations = [
        f"[{r.severity.value}] {r.title}: {r.recommendation or r.description}" for r in top
    ] or ["No action required — no risks flagged."]
    proposed_changes = [
        f"Address {r.id} ({r.category.value}): {r.recommendation or 'review with department head'}"
        for r in top
    ] or []

    total_flags = len(risks)
    if counts.get("critical"):
        impact = f"{counts['critical']} critical blocker(s) must clear before lock; expect schedule slip until resolved."
    elif counts.get("high"):
        impact = f"{counts['high']} high risk(s) across {total_flags} flag(s); add contingency day(s) and cover sets."
    elif total_flags:
        impact = f"{total_flags} lower-severity flag(s); manageable within current block."
    else:
        impact = "No schedule impact detected by local heuristics."

    n_scenes = len(analysis.scenes) if analysis else 0
    revised = (
        f"Draft revision outline for {n_scenes} scene(s): "
        f"resolve {counts.get('critical', 0)} critical / {counts.get('high', 0)} high items, "
        "consolidate night exteriors, confirm permits, clear brands/music. "
        "Re-run /api/analyze after changes to recompute readiness."
    )

    return ProductionPlan(
        readiness_score=compute_readiness(risks),
        critical_blockers=counts.get("critical", 0),
        high_risks=counts.get("high", 0),
        medium_risks=counts.get("medium", 0),
        recommendations=recommendations,
        proposed_changes=proposed_changes,
        schedule_impact=impact,
        revised_plan=revised,
    )
