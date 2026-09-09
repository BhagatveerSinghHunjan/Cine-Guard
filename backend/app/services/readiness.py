"""Deterministic production-readiness scoring (backend-owned).

Methodology (transparent, configurable via Settings):
  penalty(risk) = severity_weight[severity] × confidence_multiplier[confidence]
  mitigated risks contribute 0.
  score = clamp(100 − Σ penalties, 0, 100), rounded to 1 decimal.

Default weights: critical 15, high 5, medium 2, low 0.5.
Default confidence multipliers: high 1.0, medium 0.7, low 0.4.

Status thresholds (configurable):
  >= ready_at (80): READY · >= at_risk_at (60): AT RISK
  >= high_risk_at (40): HIGH RISK · else NOT READY.

Gemini identifies and explains risks; it NEVER invents this number.
Same risks + config always produce the same score.
"""

from app.config import get_settings
from app.models.schemas import (
    ProductionReadiness,
    ReadinessStatus,
    Risk,
    RiskConfidence,
    RiskSeverity,
    RiskStatus,
)


def _weights(settings) -> dict[str, float]:
    return {
        RiskSeverity.critical.value: settings.readiness_weight_critical,
        RiskSeverity.high.value: settings.readiness_weight_high,
        RiskSeverity.medium.value: settings.readiness_weight_medium,
        RiskSeverity.low.value: settings.readiness_weight_low,
    }


def _multipliers(settings) -> dict[str, float]:
    return {
        RiskConfidence.high.value: settings.confidence_multiplier_high,
        RiskConfidence.medium.value: settings.confidence_multiplier_medium,
        RiskConfidence.low.value: settings.confidence_multiplier_low,
    }


def risk_penalty(risk: Risk, settings=None) -> float:
    """Deterministic penalty for one risk (0 when mitigated)."""
    settings = settings or get_settings()
    if risk.status == RiskStatus.mitigated:
        return 0.0
    return _weights(settings).get(risk.severity.value, 0.0) * _multipliers(settings).get(
        risk.confidence.value if isinstance(risk.confidence, RiskConfidence) else str(risk.confidence),
        0.7,
    )


def readiness_status(score: float, settings=None) -> ReadinessStatus:
    settings = settings or get_settings()
    if score >= settings.readiness_ready_at:
        return ReadinessStatus.ready
    if score >= settings.readiness_at_risk_at:
        return ReadinessStatus.at_risk
    if score >= settings.readiness_high_risk_at:
        return ReadinessStatus.high_risk
    return ReadinessStatus.not_ready


def methodology_text(settings=None) -> str:
    settings = settings or get_settings()
    return (
        f"score = 100 − Σ(severity_weight × confidence_multiplier); "
        f"weights critical={settings.readiness_weight_critical:g}/high={settings.readiness_weight_high:g}/"
        f"medium={settings.readiness_weight_medium:g}/low={settings.readiness_weight_low:g}; "
        f"confidence ×high={settings.confidence_multiplier_high:g}/medium={settings.confidence_multiplier_medium:g}/"
        f"low={settings.confidence_multiplier_low:g}; mitigated=0; clamped 0–100. "
        f"Thresholds READY≥{settings.readiness_ready_at:g}, AT RISK≥{settings.readiness_at_risk_at:g}, "
        f"HIGH RISK≥{settings.readiness_high_risk_at:g}, else NOT READY."
    )


def score_readiness(risks: list[Risk], settings=None) -> ProductionReadiness:
    """Score a risk list deterministically."""
    from app.tools.risk_tools import count_by_severity

    settings = settings or get_settings()
    risks = risks or []
    counts = count_by_severity(risks)
    weights = _weights(settings)
    breakdown = []
    for sev in ("critical", "high", "medium", "low"):
        line_total = round(
            sum(risk_penalty(r, settings) for r in risks if r.severity.value == sev), 2
        )
        breakdown.append(
            {
                "severity": sev,
                "count": counts.get(sev, 0),
                "weight": weights.get(sev, 0.0),
                "penalty": line_total,
            }
        )
    total = round(sum(line["penalty"] for line in breakdown), 2)
    score = round(max(0.0, min(100.0, 100.0 - total)), 1)
    blockers = [
        r.id
        for r in risks
        if r.status == RiskStatus.open and r.severity in (RiskSeverity.critical, RiskSeverity.high)
    ]
    return ProductionReadiness(
        score=score,
        status=readiness_status(score, settings),
        critical_count=counts.get("critical", 0),
        high_count=counts.get("high", 0),
        medium_count=counts.get("medium", 0),
        low_count=counts.get("low", 0),
        total_risks=len(risks),
        blockers=blockers,
        methodology=methodology_text(settings),
        penalty_breakdown=breakdown,
    )
