"""CineGuard root orchestrator.

Workflow:
  Screenplay → Extraction → Research planner → Parallel → Evidence
  → Risk reasoning → Deterministic scoring → Recommendations → Fix plan

Uses ADK SequentialAgent when available; otherwise a thin local
orchestrator calling the same service layer, so /api/analyze works
offline without Gemini keys.
"""

from app.agents.planning_agent import planning_agent
from app.agents.research_agent import research_agent
from app.agents.risk_agent import risk_agent
from app.agents.screenplay_agent import screenplay_agent
from app.config import get_settings

NAME = "cineguard_root_agent"
DESCRIPTION = "Orchestrate extraction → research → risk reasoning → scoring → fix plan."
INSTRUCTION = """You are CineGuard's root coordinator.
Run screenplay extraction, plan and gather Parallel research, reason over
evidence with explicit/inferred/unknown discipline, score deterministically,
then propose mitigations. Return structured JSON only."""

settings = get_settings()
SUB_AGENTS = [screenplay_agent, research_agent, risk_agent, planning_agent]

try:
    from google.adk.agents import SequentialAgent

    root_agent = SequentialAgent(
        name=NAME,
        description=DESCRIPTION,
        sub_agents=[a for a in SUB_AGENTS if hasattr(a, "name")],
    )
except Exception:  # noqa: BLE001 -- ADK optional; local fallback keeps API working
    class _LocalRoot:
        name = NAME
        description = DESCRIPTION
        instruction = INSTRUCTION
        sub_agents = SUB_AGENTS

        def run(self, screenplay_text: str, project_title: str | None = None):
            from app.services.analysis_service import run_full_analysis

            return run_full_analysis(screenplay_text, project_title)

    root_agent = _LocalRoot()  # type: ignore


def get_root_agent():
    return root_agent


def describe_workflow() -> dict:
    live = settings.is_parallel_configured
    return {
        "root": NAME,
        "sequence": [getattr(a, "name", str(a)) for a in SUB_AGENTS],
        "research_mode": "live-parallel" if live else "not-run-no-key",
        "model": settings.gemini_model,
    }
