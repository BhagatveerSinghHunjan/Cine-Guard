"""Research Agent — deterministic planner + live Parallel Search provider.

With PARALLEL_API_KEY: live evidence with real citations.
Without: honest not-run status, zero sources — never fake citations.
"""

from app.config import get_settings
from app.tools.research_tools import plan_research_queries, run_research

NAME = "research_agent"
DESCRIPTION = "Plan research queries from dependencies; gather Parallel evidence."
INSTRUCTION = """You are the Research agent.
Turn production dependencies into bounded research queries (permits,
locations, brands, music rights, stunts, vehicles, weather). With a
configured Parallel provider you return real excerpts with source title,
domain and URL. Without one you return an honest not-run status with no
sources — never fabricate citations."""

settings = get_settings()

try:
    from google.adk.agents import Agent

    research_agent = Agent(
        name=NAME,
        model=settings.gemini_model,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        tools=[plan_research_queries, run_research],
    )
except Exception:  # noqa: BLE001 -- ADK optional; local fallback keeps API working
    class _Fallback:
        name = NAME
        description = DESCRIPTION
        instruction = INSTRUCTION

        def run(self, analysis):
            return run_research(analysis)

    research_agent = _Fallback()  # type: ignore
