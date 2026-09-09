"""Gemini-powered risk reasoning over extraction + Parallel evidence.

Gemini owns UNDERSTANDING / REASONING / CLASSIFICATION / RECOMMENDATIONS.
The backend owns VALIDATION (Pydantic) / DEDUP / SCORING / STATE.
Malformed or failed model output raises typed errors — never fake risks.
"""

import json
import logging

from pydantic import BaseModel, Field

from app.agents.risk_prompt import RISK_ANALYZER_SYSTEM_PROMPT, build_risk_prompt
from app.config import get_settings
from app.models.schemas import Recommendation, Risk, RiskDependency
from app.services.gemini_extraction import (
    GeminiAPIError,
    GeminiValidationError,
    _build_client,
    generate_content,
    parse_json_response,
)
from app.tools.risk_tools import dedup_risks

log = logging.getLogger("cineguard.risk")


class RiskReasoningResult(BaseModel):
    risks: list[Risk] = Field(default_factory=list)
    dependencies: list[RiskDependency] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)


def reason_risks_with_gemini(analysis, research: list) -> RiskReasoningResult:
    """Call Gemini with schema-constrained output. Raises typed errors."""
    settings = get_settings()
    if not settings.is_gemini_configured:
        from app.services.gemini_extraction import GeminiNotConfigured

        raise GeminiNotConfigured("Gemini credentials are not configured")

    try:
        from google.genai import types as genai_types
    except Exception as exc:  # pragma: no cover — packaging issue
        raise GeminiAPIError("Gemini client library unavailable") from exc

    analysis_json = analysis.model_dump_json()
    research_json = json.dumps([r.model_dump() for r in (research or [])])
    client = _build_client(settings)
    config = genai_types.GenerateContentConfig(
        system_instruction=RISK_ANALYZER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=RiskReasoningResult.model_json_schema(),
        temperature=0.2,
        max_output_tokens=settings.gemini_max_output_tokens,
    )
    contents = [build_risk_prompt(analysis_json, research_json)]
    # Retry malformed structured output only; auth/timeout/API raise at once.
    for _ in range(max(1, settings.gemini_parse_attempts)):
        raw = generate_content(client, settings.gemini_model, contents, config, settings)
        try:
            payload = parse_json_response(raw)
        except GeminiValidationError:
            log.warning("Gemini risk parse attempt failed, retrying")
            continue
        break
    else:  # pragma: no cover — defensive
        raise GeminiValidationError("Gemini returned malformed JSON")
    try:
        result = RiskReasoningResult.model_validate(payload)
    except Exception as exc:
        raise GeminiValidationError(
            "Gemini risk output failed schema validation"
        ) from exc
    # Backend-owned post-processing: dedup is deterministic, never the model.
    result.risks = dedup_risks(result.risks)
    return result
