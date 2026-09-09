"""Heuristic local risk assessment (no external data).

Transparent, deterministic rules so tests and demos behave identically
with or without Gemini/Parallel configured. Every risk carries:
- why_it_matters (production implication, not a summary)
- evidence_items labeled screenplay (quoted text) or inference (reasoning)
- confidence / status / affected_scenes
Research-kind evidence is NEVER fabricated here — only the Gemini path
(which receives real Parallel evidence) may attach it.
"""

import re

from app.models.schemas import (
    DependencyRelationship,
    EvidenceItem,
    EvidenceKind,
    Recommendation,
    RecommendationAction,
    Risk,
    RiskCategory,
    RiskConfidence,
    RiskDependency,
    RiskSeverity,
    RiskStatus,
    ScreenplayAnalysis,
)

_ACTION_BY_CATEGORY = {
    RiskCategory.location: RecommendationAction.replace_location,
    RiskCategory.schedule: RecommendationAction.change_schedule,
    RiskCategory.permit: RecommendationAction.obtain_permit,
    RiskCategory.cast: RecommendationAction.confirm_cast,
    RiskCategory.vehicle: RecommendationAction.source_vehicle,
    RiskCategory.music: RecommendationAction.replace_music,
    RiskCategory.brand: RecommendationAction.review_brand,
    RiskCategory.stunt: RecommendationAction.plan_stunt,
    RiskCategory.vfx: RecommendationAction.prepare_vfx,
    RiskCategory.weather: RecommendationAction.change_schedule,
    RiskCategory.equipment: RecommendationAction.other,
    RiskCategory.continuity: RecommendationAction.other,
    RiskCategory.legal: RecommendationAction.obtain_permit,
    RiskCategory.other: RecommendationAction.other,
}

_PRIORITY = {"critical": 1, "high": 2, "medium": 3, "low": 4}


def _mk(
    rid: str,
    category: RiskCategory,
    severity: RiskSeverity,
    title: str,
    description: str,
    scene_number: int | None = None,
    evidence: str = "",
    recommendation: str = "",
    deps: list[str] | None = None,
    why_it_matters: str = "",
    confidence: RiskConfidence = RiskConfidence.high,
    affected_scenes: list[int] | None = None,
    inference: str = "",
) -> Risk:
    items: list[EvidenceItem] = []
    if evidence:
        items.append(
            EvidenceItem(
                kind=EvidenceKind.screenplay,
                text=evidence,
                scene_numbers=[scene_number] if scene_number else [],
            )
        )
    if inference:
        items.append(EvidenceItem(kind=EvidenceKind.inference, text=inference))
    scenes = sorted(set(affected_scenes or ([scene_number] if scene_number else [])))
    return Risk(
        id=rid,
        scene_number=scene_number,
        affected_scenes=scenes,
        category=category,
        severity=severity,
        title=title,
        description=description,
        why_it_matters=why_it_matters or description,
        evidence=evidence,
        evidence_items=items,
        recommendation=recommendation,
        affected_dependencies=deps or [],
        confidence=confidence,
        status=RiskStatus.open,
    )


def derive_unknowns(analysis: ScreenplayAnalysis) -> list[str]:
    """Deterministic unknowns: facts a producer needs that text can't establish.

    These are surfaced, never guessed — an explicit trust feature.
    """
    unknowns: list[str] = []
    if analysis.scenes:
        unknowns.append(
            "Whether required filming permits have already been secured is unknown."
        )
    if analysis.characters:
        unknowns.append(
            "Cast availability for the scheduled scenes is unknown."
        )
    if analysis.weather_dependencies:
        unknowns.append(
            f"Weather certainty for "
            f"{', '.join(analysis.weather_dependencies[:3])} is unknown — "
            "cover planning is advised."
        )
    if analysis.locations:
        unknowns.append(
            "Location approval and access terms for "
            f"{', '.join(analysis.locations[:3])} are unknown."
        )
    if analysis.brands or analysis.music:
        unknowns.append(
            "Clearance status for branded or musical assets is unknown."
        )
    return unknowns


def assess_risks(analysis: ScreenplayAnalysis) -> list[Risk]:
    risks: list[Risk] = []
    n = 1

    def nid() -> str:
        nonlocal n
        r = f"R-{n:03d}"
        n += 1
        return r

    for scene in analysis.scenes or []:
        reqs = {r.lower() for r in scene.production_requirements}
        desc_snippet = (scene.description or "")[:180]

        if reqs & {"chase", "explosion", "gunfight", "stunt", "crash"}:
            risks.append(
                _mk(
                    nid(),
                    RiskCategory.stunt,
                    RiskSeverity.high,
                    f"Stunt / action complexity (Scene {scene.scene_number})",
                    "Action beat requires coordinator, safety rehearsal and permits.",
                    scene.scene_number,
                    desc_snippet,
                    "Hire stunt coordinator; board extra safety day; confirm permits.",
                    sorted(reqs),
                    why_it_matters="Without a coordinator and safety rehearsal, the shoot day cannot run and insurance may not cover the sequence.",
                    inference="Stunt keywords in the scene imply specialist personnel and extra setup time.",
                )
            )
        if reqs & {"helicopter", "plane", "drone shot"}:
            risks.append(
                _mk(
                    nid(),
                    RiskCategory.permit,
                    RiskSeverity.high,
                    f"Aerial permit likely (Scene {scene.scene_number})",
                    "Aerial work typically needs aviation authority + location permits.",
                    scene.scene_number,
                    desc_snippet,
                    "Confirm aerial permit path or swap to ground-based coverage.",
                    sorted(reqs),
                    why_it_matters="Aerial units book out and permits take weeks; without them the scene cannot be shot as written.",
                    inference="Aerial keywords imply regulated airspace and municipal permits.",
                )
            )
        if "night" in (scene.time_of_day or "").lower() and "ext" in scene.heading.lower():
            risks.append(
                _mk(
                    nid(),
                    RiskCategory.schedule,
                    RiskSeverity.medium,
                    "Night exterior shooting",
                    "Night exteriors constrain hours, lighting kit and turnaround.",
                    scene.scene_number,
                    scene.heading,
                    "Consolidate night exteriors into consecutive night shoots.",
                    ["night", "lighting"],
                    why_it_matters="Night units cost more per hour and limit turnaround; scattered night shoots inflate the schedule.",
                    inference="A night exterior implies lighting package, generator and restricted shooting window.",
                )
            )

    if analysis.brands:
        risks.append(
            _mk(
                nid(),
                RiskCategory.brand,
                RiskSeverity.medium,
                "Visible brand references need clearance",
                f"Brands detected: {', '.join(analysis.brands[:5])}. May need trademark clearance.",
                None,
                ", ".join(analysis.brands[:5]),
                "Clear, blur, or replace with fictional brands.",
                analysis.brands,
                why_it_matters="Uncleared trademarks can force costly reshoots or edits after distribution is locked.",
                inference="Real-world brand names on screen imply trademark review.",
            )
        )
    if analysis.music:
        risks.append(
            _mk(
                nid(),
                RiskCategory.music,
                RiskSeverity.medium,
                "Music cues need licensing",
                "Audible/commercial music cues require sync licensing.",
                None,
                ", ".join(analysis.music[:5]),
                "Commission score or license library equivalents early.",
                analysis.music,
                why_it_matters="Sync licenses take weeks and can exceed the music budget if left late.",
                inference="Audible song references imply rights-holder negotiation.",
            )
        )
    if analysis.vfx_requirements:
        risks.append(
            _mk(
                nid(),
                RiskCategory.vfx,
                RiskSeverity.medium,
                "VFX shots need breakdown",
                f"VFX cues: {', '.join(analysis.vfx_requirements[:5])}.",
                None,
                ", ".join(analysis.vfx_requirements[:5]),
                "Get VFX breakdown + bid before locking schedule.",
                analysis.vfx_requirements,
                why_it_matters="Unbid VFX routinely overruns post budgets and delivery dates.",
                inference="VFX keywords imply vendor bids and longer post time.",
            )
        )
    if analysis.weather_dependencies:
        risks.append(
            _mk(
                nid(),
                RiskCategory.weather,
                RiskSeverity.high,
                "Weather-dependent exteriors",
                f"Weather cues: {', '.join(analysis.weather_dependencies[:5])}.",
                None,
                ", ".join(analysis.weather_dependencies[:5]),
                "Add weather cover sets / alternate days.",
                analysis.weather_dependencies,
                why_it_matters="Weather holds idle the full unit; without cover sets each lost day burns budget.",
                inference="Weather keywords imply cover-set planning and contingency days.",
            )
        )
    if len(analysis.locations) > 5:
        risks.append(
            _mk(
                nid(),
                RiskCategory.location,
                RiskSeverity.medium,
                "High location count",
                f"{len(analysis.locations)} distinct locations increase company moves.",
                None,
                ", ".join(analysis.locations[:5]),
                "Consolidate locations or block-shoot by zone.",
                analysis.locations[:8],
                why_it_matters="Every company move costs hours; too many locations cascade into overtime and turnaround violations.",
                inference="Location count above five implies frequent moves.",
            )
        )

    if not risks and analysis.scenes:
        risks.append(
            _mk(
                nid(),
                RiskCategory.other,
                RiskSeverity.low,
                "No major local risk signals",
                "Heuristic scan found no stunt/permit/brand/music/VFX flags.",
                None,
                "",
                "Proceed to creative review; external research may surface more.",
                [],
                why_it_matters="Low signal now, but research and detailed review can still surface issues.",
                confidence=RiskConfidence.low,
            )
        )
    return dedup_risks(risks)


def _canonical_title(title: str) -> str:
    return re.sub(r"\s*\(Scene\s+\d+\)\s*$", "", title).strip()


def dedup_risks(risks: list[Risk]) -> list[Risk]:
    """Merge risks with identical (category, severity, canonical title).

    Scenes 12+13+14 depending on the same problem become ONE risk with
    affected_scenes=[12, 13, 14] instead of three duplicates.
    """
    merged: dict[tuple, Risk] = {}
    order: list[tuple] = []
    for r in risks or []:
        key = (r.category, r.severity, _canonical_title(r.title))
        if key not in merged:
            merged[key] = r.model_copy(deep=True)
            order.append(key)
            continue
        cur = merged[key]
        scenes = sorted(set(cur.affected_scenes) | set(r.affected_scenes))
        cur.affected_scenes = scenes
        cur.scene_number = scenes[0] if len(scenes) == 1 else None
        deps = list(cur.affected_dependencies)
        for d in r.affected_dependencies:
            if d not in deps:
                deps.append(d)
        cur.affected_dependencies = deps
        for item in r.evidence_items:
            if item.text and all(e.text != item.text for e in cur.evidence_items):
                cur.evidence_items.append(item)
        if len(cur.title) < len(r.title):
            pass  # keep the shorter canonical title
        else:
            cur.title = _canonical_title(r.title)
    out = [merged[k] for k in order]
    # Canonical titles for merged risks (drop the single-scene suffix).
    for r in out:
        if len(r.affected_scenes) > 1:
            r.title = _canonical_title(r.title)
    return out


def _scenes_of(risk: Risk) -> set[int]:
    s = set(risk.affected_scenes)
    if risk.scene_number is not None:
        s.add(risk.scene_number)
    return s


def build_dependency_edges(risks: list[Risk]) -> list[RiskDependency]:
    """Deterministic dependency graph between risks sharing scenes."""
    edges: list[RiskDependency] = []
    n = 1
    blockers = [r for r in risks if r.category in (RiskCategory.location, RiskCategory.permit)]
    weather = [r for r in risks if r.category == RiskCategory.weather]
    schedule = [r for r in risks if r.category == RiskCategory.schedule]
    movers = [r for r in risks if r.category in (RiskCategory.stunt, RiskCategory.vehicle)]

    def add(src: Risk, tgt: Risk, rel, impact: str):
        nonlocal n
        if src.id == tgt.id:
            return
        if any(e.source_risk_id == src.id and e.target_risk_id == tgt.id for e in edges):
            return
        edges.append(
            RiskDependency(
                id=f"D-{n:03d}",
                source_risk_id=src.id,
                target_risk_id=tgt.id,
                relationship=rel,
                impact=impact,
            )
        )
        n += 1

    for b in blockers:
        for m in movers:
            if _scenes_of(b) & _scenes_of(m):
                scenes = sorted(_scenes_of(b) & _scenes_of(m))
                add(
                    b,
                    m,
                    DependencyRelationship.blocks,
                    f"Scenes {scenes} cannot shoot the action until access/permits clear.",
                )
    for w in weather:
        w_scenes = _scenes_of(w)
        for m in movers + schedule:
            m_scenes = _scenes_of(m)
            # Global weather risk affects all scene-bound work; scoped weather
            # affects only overlapping scenes.
            if m_scenes and (not w_scenes or (w_scenes & m_scenes)):
                add(
                    w,
                    m,
                    DependencyRelationship.affects,
                    "Weather exposure can delay the dependent work.",
                )
    for s in schedule:
        for m in movers:
            if _scenes_of(s) & _scenes_of(m):
                add(
                    s,
                    m,
                    DependencyRelationship.affects,
                    "Night/schedule constraints compress the action unit's window.",
                )
    return edges


def generate_recommendations(risks: list[Risk]) -> list[Recommendation]:
    """One actionable recommendation per open risk (priority = severity)."""
    recs: list[Recommendation] = []
    n = 1
    for r in sorted(risks or [], key=lambda x: (_PRIORITY.get(x.severity.value, 4), x.id)):
        if r.status != RiskStatus.open or r.category == RiskCategory.other:
            continue
        action = _ACTION_BY_CATEGORY.get(r.category, RecommendationAction.other)
        scenes = sorted(_scenes_of(r))
        where = f" (Scenes {scenes})" if scenes else ""
        recs.append(
            Recommendation(
                id=f"REC-{n:03d}",
                priority=_PRIORITY.get(r.severity.value, 4),
                title=f"{r.title}{where}: {r.recommendation or 'assign an owner and a due date'}",
                description=r.why_it_matters,
                addresses_risk_ids=[r.id],
                expected_impact=f"Resolving removes the {r.severity.value} penalty for {r.id}.",
                action_type=action,
            )
        )
        n += 1
    return recs


def count_by_severity(risks: list[Risk]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in risks:
        counts[r.severity.value] = counts.get(r.severity.value, 0) + 1
    return counts
