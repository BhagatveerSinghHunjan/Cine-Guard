"""Production Planning Agent — deterministic fix plans over stored runs."""

from app.config import get_settings
from app.services.fixplan import build_fix_plan
from app.tools.planning_tools import build_plan

NAME = "production_planning_agent"
DESCRIPTION = "Build deterministic mitigation plans; backend calculates projected readiness."
INSTRUCTION = """You are the Production Planning agent.
Given risks, dependencies, recommendations and current readiness, propose
concrete mitigation actions. You NEVER invent the projected readiness —
the backend re-scores deterministically after applying mitigations and
reports remaining blockers."""

settings = get_settings()

try:
    from google.adk.agents import Agent

    planning_agent = Agent(
        name=NAME,
        model=settings.gemini_model,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        tools=[build_fix_plan, build_plan],
    )
except Exception:  # noqa: BLE001 -- ADK optional; local fallback keeps API working
    class _Fallback:
        name = NAME
        description = DESCRIPTION
        instruction = INSTRUCTION

        def run(self, risks, recommendations, selected_ids):
            return build_fix_plan(risks, recommendations, selected_ids)

    planning_agent = _Fallback()  # type: ignore
