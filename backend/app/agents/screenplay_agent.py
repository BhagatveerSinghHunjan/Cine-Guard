"""Screenplay Analysis Agent — structured extraction via Gemini (heuristic fallback)."""

from app.agents.screenplay_prompt import SCREENPLAY_ANALYZER_SYSTEM_PROMPT
from app.config import get_settings
from app.tools.screenplay_tools import parse_screenplay_text

NAME = "screenplay_analysis_agent"
DESCRIPTION = (
    "Extract structured production data (scenes, characters, locations, "
    "dependencies, concerns) with explicit/inferred/unknown evidence levels."
)
INSTRUCTION = SCREENPLAY_ANALYZER_SYSTEM_PROMPT

settings = get_settings()

try:
    from google.adk.agents import Agent

    screenplay_agent = Agent(
        name=NAME,
        model=settings.gemini_model,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        tools=[parse_screenplay_text],
    )
except Exception:  # noqa: BLE001 -- ADK unavailable offline, local fallback keeps API working
    class _Fallback:
        name = NAME
        description = DESCRIPTION
        instruction = INSTRUCTION

        def run(self, screenplay_text: str, project_title: str | None = None):
            return parse_screenplay_text(screenplay_text, project_title)

    screenplay_agent = _Fallback()  # type: ignore
