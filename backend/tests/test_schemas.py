"""Schema validation tests — missing optional fields must not crash."""

import pytest
from pydantic import ValidationError

from app.models.schemas import Risk, RiskCategory, RiskSeverity, Scene, ScreenplayAnalysis


def test_scene_defaults():
    s = Scene(scene_number=1)
    assert s.heading == ""
    assert s.characters == []
    assert s.production_requirements == []


def test_screenplay_missing_fields_ok():
    a = ScreenplayAnalysis()
    assert a.project_title == "Untitled"
    assert a.scenes == []
    assert a.brands == []


def test_risk_requires_core_fields():
    with pytest.raises(ValidationError):
        Risk(category=RiskCategory.stunt, severity=RiskSeverity.high)  # type: ignore


def test_risk_severity_enum_rejects_unknown():
    with pytest.raises(ValidationError):
        Risk(
            id="R-1",
            category=RiskCategory.stunt,
            severity="extreme",  # type: ignore
            title="t",
            description="d",
        )


def test_risk_scene_number_optional():
    r = Risk(
        id="R-001",
        category=RiskCategory.brand,
        severity=RiskSeverity.medium,
        title="Brand",
        description="needs clearance",
    )
    assert r.scene_number is None
    assert r.affected_dependencies == []
