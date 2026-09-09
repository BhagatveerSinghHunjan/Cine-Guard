"""Risk Analysis Agent — evidence-aware reasoning over extraction + research."""

from app.agents.risk_prompt import RISK_ANALYZER_SYSTEM_PROMPT
from app.config import get_settings
from app.tools.risk_tools import assess_risks

NAME = "risk_analysis_agent"
DESCRIPTION = (
    "Reason over screenplay facts, inferences, unknowns, dependencies and "
    "Parallel research evidence. Answer: what could prevent or complicate production?"
)
INSTRUCTION = RISK_ANALYZER_SYSTEM_PROMPT

settings = get_settings()

try:
    from google.adk.agents import Agent

    risk_agent = Agent(
        name=NAME,
        model=settings.gemini_model,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        tools=[assess_risks],
    )
except Exception:  # noqa: BLE001 -- ADK optional; local fallback keeps API working
    class _Fallback:
        name = NAME
        description = DESCRIPTION
        instruction = INSTRUCTION

        def run(self, analysis):
            return assess_risks(analysis)

    risk_agent = _Fallback()  # type: ignore
