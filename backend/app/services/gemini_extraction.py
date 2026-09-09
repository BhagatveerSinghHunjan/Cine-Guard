"""Gemini-powered structured screenplay extraction.

Pipeline: prompt (screenplay_prompt) → Gemini with response_schema →
raw JSON → Pydantic validation → ScreenplayAnalysis.

No secrets ever leave the server: errors are mapped to safe messages.
Without credentials the caller falls back to the local heuristic parser.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from app.agents.screenplay_prompt import (
    SCREENPLAY_ANALYZER_SYSTEM_PROMPT,
    build_user_prompt,
)
from app.config import get_settings
from app.models.schemas import ScreenplayAnalysis
from app.tools.screenplay_tools import parse_screenplay_text

log = logging.getLogger("cineguard.gemini")


class GeminiExtractionError(Exception):
    """Base — never carries secrets."""


class GeminiNotConfigured(GeminiExtractionError):
    pass


class GeminiAuthError(GeminiExtractionError):
    pass


class GeminiTimeoutError(GeminiExtractionError):
    pass


class GeminiAPIError(GeminiExtractionError):
    pass


class GeminiValidationError(GeminiExtractionError):
    pass


class InputTooLargeError(ValueError):
    pass


def is_gemini_available() -> bool:
    return get_settings().is_gemini_configured


def chunk_screenplay(text: str, max_chars: int) -> list[str]:
    """Future chunking seam. MVP: single chunk or raise.

    Raises InputTooLargeError instead of silently truncating.
    """
    if len(text) <= max_chars:
        return [text]
    raise InputTooLargeError(
        f"Screenplay is {len(text):,} characters; limit is {max_chars:,}. "
        "Shorten the input or wait for chunked processing (planned)."
    )


def _strip_fences(raw: str) -> str:
    s = (raw or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _is_auth_failure(err: Exception) -> bool:
    msg = f"{type(err).__name__}: {err}".lower()
    return any(
        token in msg
        for token in (
            "unauthenticated",
            "permission denied",
            "api key",
            "api_key",
            "invalid key",
            "401",
            "403",
        )
    )


def _is_timeout(err: Exception) -> bool:
    msg = f"{type(err).__name__}: {err}".lower()
    return "timeout" in msg or "timed out" in msg or "deadline" in msg


def _build_client(settings):
    from google import genai

    if settings.gemini_api_key:
        return genai.Client(api_key=settings.gemini_api_key)
    return genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )


def generate_content(client, model: str, contents, config, settings) -> str:
    """One Gemini call with an enforced wall-clock timeout.

    Maps failures to typed errors without secrets. The genai SDK offers no
    per-request timeout, so the call runs in a worker thread joined at
    settings.gemini_timeout_seconds.
    """
    def _call():
        return client.models.generate_content(
            model=model, contents=contents, config=config
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_call)
        try:
            response = future.result(timeout=settings.gemini_timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            raise GeminiTimeoutError(
                "Gemini request timed out — retry shortly"
            ) from exc
        except Exception as exc:
            if _is_auth_failure(exc):
                log.warning("Gemini auth failure: %s", type(exc).__name__)
                raise GeminiAuthError(
                    "Gemini authentication failed — check server GEMINI_API_KEY / project"
                ) from exc
            if _is_timeout(exc):
                raise GeminiTimeoutError("Gemini request timed out — retry shortly") from exc
            log.warning("Gemini API error: %s", type(exc).__name__)
            raise GeminiAPIError("Gemini request failed — retry shortly") from exc
    raw = getattr(response, "text", "") or ""
    if not raw.strip():
        raise GeminiValidationError("Gemini returned an empty response")
    return raw


def parse_json_response(raw: str):
    """Parse model JSON (fences tolerated). Raises GeminiValidationError."""
    try:
        return json.loads(_strip_fences(raw))
    except json.JSONDecodeError as exc:
        raise GeminiValidationError("Gemini returned malformed JSON") from exc


def extract_with_gemini(
    screenplay_text: str, project_title: str | None = None
) -> ScreenplayAnalysis:
    """Call Gemini with schema-constrained output. Raises typed errors."""
    settings = get_settings()
    text = (screenplay_text or "").strip()
    if not text:
        raise ValueError("screenplay_text must not be empty")
    if len(text) > settings.max_screenplay_chars:
        raise InputTooLargeError(
            f"Screenplay is {len(text):,} characters; limit is "
            f"{settings.max_screenplay_chars:,}. Shorten the input."
        )
    if not settings.is_gemini_configured:
        raise GeminiNotConfigured("Gemini credentials are not configured")

    try:
        from google.genai import types as genai_types
    except Exception as exc:  # pragma: no cover — packaging issue
        raise GeminiAPIError("Gemini client library unavailable") from exc

    schema = ScreenplayAnalysis.model_json_schema()
    # genai expects plain JSON-schema dicts; drop $defs refs issues by inlining.
    client = _build_client(settings)
    config = genai_types.GenerateContentConfig(
        system_instruction=SCREENPLAY_ANALYZER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.1,
        max_output_tokens=settings.gemini_max_output_tokens,
    )

    # Retry malformed/empty structured output only — auth, timeout and API
    # errors raise immediately (retrying those would mask real outages).
    for _ in range(max(1, settings.gemini_parse_attempts)):
        raw = generate_content(
            client, settings.gemini_model,
            [build_user_prompt(text, project_title)], config, settings,
        )
        try:
            payload = parse_json_response(raw)
        except GeminiValidationError:
            log.warning("Gemini parse attempt failed, retrying")
            continue
        break
    else:  # pragma: no cover — defensive; loop always breaks or raises above
        raise GeminiValidationError("Gemini returned malformed JSON")

    # Backfill title: explicit request title wins; else model or heuristic title.
    if (project_title or "").strip() and isinstance(payload, dict):
        payload.setdefault("project_title", project_title.strip())

    try:
        analysis = ScreenplayAnalysis.model_validate(payload)
    except Exception as exc:
        raise GeminiValidationError(
            "Gemini output failed schema validation — retry or simplify input"
        ) from exc

    if (project_title or "").strip():
        analysis.project_title = project_title.strip()
    if analysis.project is None and analysis.project_title:
        from app.models.schemas import ProjectInfo

        analysis.project = ProjectInfo(title=analysis.project_title)
    _sync_flat_lists(analysis)
    return analysis


def _sync_flat_lists(analysis: ScreenplayAnalysis) -> None:
    """Derive flat convenience lists from detailed entries (Gemini path).

    Keeps older frontend versions working: flat lists always reflect detail.
    """
    if analysis.characters_detailed and not analysis.characters:
        analysis.characters = [c.name for c in analysis.characters_detailed]
    if analysis.locations_detailed and not analysis.locations:
        analysis.locations = [loc.name for loc in analysis.locations_detailed]
    if not analysis.production_dependencies:
        merged: list[str] = []
        for bucket in (
            analysis.props,
            analysis.vehicles,
            analysis.brands,
            analysis.music,
            analysis.stunts,
            analysis.vfx_requirements,
            analysis.weather_dependencies,
            analysis.time_dependencies,
            analysis.special_equipment,
        ):
            for item in bucket or []:
                if item not in merged:
                    merged.append(item)
        analysis.production_dependencies = merged


def extract_heuristic_fallback(
    screenplay_text: str, project_title: str | None = None
) -> ScreenplayAnalysis:
    """Local parser enriched with unknown-evidence defaults for new fields."""
    analysis = parse_screenplay_text(screenplay_text, project_title)
    # Heuristic path: flat lists are authoritative; detailed lists stay empty
    # (honest — we do not fabricate roles/types), concerns stay empty
    # (risk agent owns heuristic concerns downstream).
    return analysis
