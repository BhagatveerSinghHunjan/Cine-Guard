"""Deterministic local screenplay parser (no LLM, no network).

Converts raw screenplay text into ScreenplayAnalysis. Tolerant of
missing sections — every field falls back to a safe default.
"""

import re

from app.models.schemas import (
    EvidenceLevel,
    InteriorExterior,
    Scene,
    ScreenplayAnalysis,
)

SCENE_HEADING_RE = re.compile(
    r"^\s*(INT\.|EXT\.|INT\./EXT\.|EXT\./INT\.|INT\/EXT|SCENE\s+\d+)", re.IGNORECASE
)
TIME_TOKENS = ["DAY", "NIGHT", "DAWN", "DUSK", "MORNING", "EVENING", "LATER", "CONTINUOUS"]
CHARACTER_RE = re.compile(r"^[A-Z][A-Z0-9 .'\-]{1,29}$")

KEYWORDS: dict[str, list[str]] = {
    "vehicles": ["car", "truck", "helicopter", "motorcycle", "boat", "plane", "chase"],
    "brands": ["coca-cola", "coke", "nike", "apple", "iphone", "ferrari", "mcdonald",
               "zestpop", "nova cola"],
    "music": ["song", "track", "band plays", "concert", "radio plays", "hums"],
    "stunts": ["chase", "explosion", "fight", "jump", "crash", "stunt", "gunfight"],
    "vfx_requirements": ["cgi", "green screen", "vfx", "drone shot", "de-aging", "creature"],
    "weather_dependencies": ["rain", "storm", "snow", "desert heat", "fog", "hurricane"],
    "time_dependencies": ["sunset", "sunrise", "midnight", "golden hour"],
    "props": ["gun", "sword", "laptop", "phone", "briefcase", "mask"],
}


def _extract_time_of_day(heading: str) -> str:
    upper = heading.upper()
    for tok in TIME_TOKENS:
        if tok in upper:
            return tok.capitalize()
    return ""


def _extract_location(heading: str) -> str:
    cleaned = re.sub(
        r"^\s*(INT\.|EXT\.|INT\./EXT\.|EXT\./INT\.|INT\/EXT|SCENE\s+\d+)\s*",
        "",
        heading,
        flags=re.IGNORECASE,
    )
    cleaned = re.split(r"\s*[-–]\s*", cleaned)[0]
    return cleaned.strip().strip(".")[:120]


def _extract_interior_exterior(heading: str) -> InteriorExterior:
    upper = (heading or "").upper()
    has_int = "INT." in upper or upper.startswith("INT ") or "INT./EXT" in upper
    has_ext = "EXT." in upper or upper.startswith("EXT ") or "EXT./INT" in upper
    if has_int and has_ext:
        return InteriorExterior.int_ext
    if has_int:
        return InteriorExterior.interior
    if has_ext:
        return InteriorExterior.exterior
    return InteriorExterior.unknown


def parse_screenplay_text(
    screenplay_text: str, project_title: str | None = None
) -> ScreenplayAnalysis:
    """Parse raw text. Never raises on missing fields; returns defaults."""
    text = (screenplay_text or "").strip()
    title = (project_title or "").strip() or "Untitled"

    # Title fallback: first non-empty line if it looks like a title.
    if not project_title:
        for line in text.splitlines()[:5]:
            s = line.strip()
            if s and len(s) < 80 and not SCENE_HEADING_RE.match(s):
                title = s
                break

    # Split into scene blocks on headings.
    lines = text.splitlines()
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if SCENE_HEADING_RE.match(line):
            if current:
                blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    if not blocks:
        blocks = [lines] if lines else [[]]

    scenes: list[Scene] = []
    all_chars: list[str] = []
    buckets: dict[str, list[str]] = {k: [] for k in KEYWORDS}

    for i, block in enumerate(blocks, start=1):
        heading = block[0].strip() if block else ""
        if not SCENE_HEADING_RE.match(heading):
            heading = f"SCENE {i}"
        body = "\n".join(block[1:] if len(block) > 1 else block)
        body_lower = body.lower()

        chars: list[str] = []
        for line in block[1:]:
            s = line.strip()
            if CHARACTER_RE.match(s) and s.lower() not in ("cut to", "fade in", "fade out"):
                name = s.title()
                if name not in chars:
                    chars.append(name)
                if name not in all_chars:
                    all_chars.append(name)

        requirements: list[str] = []
        for bucket, words in KEYWORDS.items():
            for w in words:
                if w in body_lower and w not in buckets[bucket]:
                    buckets[bucket].append(w)
                if w in body_lower and w not in requirements:
                    requirements.append(w)

        scenes.append(
            Scene(
                scene_number=i,
                heading=heading[:200],
                interior_or_exterior=_extract_interior_exterior(heading),
                location=_extract_location(heading),
                time_of_day=_extract_time_of_day(heading),
                characters=chars,
                description=body.strip()[:2000],
                production_requirements=requirements,
                evidence_level=EvidenceLevel.explicit,
            )
        )

    locations = sorted({s.location for s in scenes if s.location})
    prod_deps = sorted(
        {d for s in scenes for d in s.production_requirements}
    )

    return ScreenplayAnalysis(
        project_title=title,
        scenes=scenes,
        characters=all_chars,
        locations=locations,
        props=buckets["vehicles"][:0] + buckets["props"],
        vehicles=buckets["vehicles"],
        brands=buckets["brands"],
        music=buckets["music"],
        stunts=buckets["stunts"],
        vfx_requirements=buckets["vfx_requirements"],
        weather_dependencies=buckets["weather_dependencies"],
        time_dependencies=buckets["time_dependencies"],
        production_dependencies=prod_deps,
    )
