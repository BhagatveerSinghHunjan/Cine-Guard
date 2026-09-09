"""Deterministic fix-plan builder (backend-owned calculation).

Gemini/heuristic propose recommendations; THIS service computes:
- which risks each selected recommendation mitigates (open + addressed)
- projected readiness by re-scoring with mitigated risks at 0 penalty
- remaining blockers, schedule impact, revised plan text

The model NEVER claims a projected number — the backend calculates it.
"""

from app.models.schemas import (
    FixPlan,
    PlanAction,
    ProductionReadiness,
    Recommendation,
    Risk,
    RiskSeverity,
    RiskStatus,
)
from app.services.readiness import risk_penalty, score_readiness

_SCHEDULE_BY_ACTION = {
    "replace_location": "Location swap needs scouting + re-permit; allow 1–2 weeks.",
    "change_schedule": "Re-block affected scenes into contiguous units; check turnaround.",
    "obtain_permit": "Permit lead time dominates — file immediately, hold dates as tentative.",
    "confirm_cast": "Confirm availability before locking adjacent units.",
    "source_vehicle": "Picture-vehicle booking typically needs 1–2 weeks lead.",
    "replace_music": "Replacement cues need editorial + legal review time.",
    "review_brand": "Clearance review is fast if started now; slow if left to post.",
    "plan_stunt": "Stunt prep needs coordinator + rehearsal day before the unit call.",
    "prepare_vfx": "VFX bidding extends prep; lock plates early.",
    "other": "Assign an owner and a due date; track to close.",
}


def _scenes_of(risk: Risk) -> list[int]:
    s = set(risk.affected_scenes)
    if risk.scene_number is not None:
        s.add(risk.scene_number)
    return sorted(s)


def build_fix_plan(
    risks: list[Risk],
    recommendations: list[Recommendation],
    selected_ids: list[str],
    settings=None,
) -> FixPlan:
    risks = [r.model_copy(deep=True) for r in (risks or [])]
    by_rec = {rec.id: rec for rec in (recommendations or [])}
    by_risk = {r.id: r for r in risks}

    selected = [by_rec[i] for i in (selected_ids or []) if i in by_rec]
    mitigated_ids: list[str] = []
    actions: list[PlanAction] = []
    total_reduction = 0.0

    for k, rec in enumerate(selected, start=1):
        newly: list[str] = []
        reduction = 0.0
        scenes: set[int] = set()
        for rid in rec.addresses_risk_ids:
            target = by_risk.get(rid)
            if target is None or target.status != RiskStatus.open:
                continue
            reduction += risk_penalty(target, settings)
            target.status = RiskStatus.mitigated
            newly.append(rid)
            scenes.update(_scenes_of(target))
        if not newly:
            continue
        mitigated_ids.extend(newly)
        total_reduction += reduction
        actions.append(
            PlanAction(
                id=f"ACT-{k:03d}",
                recommendation_id=rec.id,
                title=rec.title,
                description=rec.description,
                affected_scenes=sorted(scenes),
                affected_risk_ids=newly,
                expected_risk_reduction=round(reduction, 1),
                schedule_impact=_SCHEDULE_BY_ACTION.get(rec.action_type.value, _SCHEDULE_BY_ACTION["other"]),
            )
        )

    projected: ProductionReadiness = score_readiness(risks, settings)
    remaining = [
        r.id
        for r in risks
        if r.status == RiskStatus.open
        and r.severity in (RiskSeverity.critical, RiskSeverity.high)
    ]
    improvements = [
        f"{a.id} ({a.recommendation_id}): mitigated {', '.join(a.affected_risk_ids)} "
        f"−{a.expected_risk_reduction:.1f} pts"
        for a in actions
    ]
    if actions:
        impact = f"{len(actions)} mitigation action(s) covering {len(mitigated_ids)} risk(s)."
        if remaining:
            impact += f" {len(remaining)} blocker(s) still open."
        else:
            impact += " No critical/high blockers remain."
        revised = (
            f"Execute {len(actions)} action(s) in priority order, re-verify each "
            f"mitigated risk on the day, then re-run analysis to confirm readiness."
        )
    else:
        impact = "No recommendations selected or all addressed risks already mitigated."
        revised = "Select at least one recommendation to generate a mitigation plan."

    return FixPlan(
        actions=actions,
        affected_risk_ids=mitigated_ids,
        projected_readiness=projected,
        remaining_blockers=remaining,
        schedule_impact=impact,
        revised_plan=revised,
        improvements=improvements,
    )
