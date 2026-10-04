"""Scenario keys (FR-###, SC-###, USn, USn/ACn) found in prose and in test names."""

from __future__ import annotations

import re

_EDGE = r"(?<![A-Za-z0-9])"
_END = r"(?![A-Za-z0-9])"
_REQ = r"(?P<req>FR|SC)[-_]?(?P<num>\d{3})"
_STORY = r"(?P<story>US\d+)(?:[-_/ ]?(?P<ac>AC\d+))?"
KEY = re.compile(f"{_EDGE}(?:{_REQ}|{_STORY}){_END}", re.IGNORECASE)
STORY = re.compile(r"(US\d+)(?:/AC\d+)?")


def _canonical(match: re.Match[str]) -> str:
    if match["req"]:
        return f"{match['req'].upper()}-{match['num']}"
    story = match["story"].upper()
    return f"{story}/{match['ac'].upper()}" if match["ac"] else story


def keys_in(text: str) -> list[str]:
    """Canonical keys in text, unique, in first-seen order."""
    return list(dict.fromkeys(_canonical(match) for match in KEY.finditer(text)))


def story_of(key: str) -> str | None:
    """The story a canonical key belongs to: US1/AC2 -> US1, US3 -> US3, FR-003 -> None."""
    match = STORY.fullmatch(key)
    return match[1] if match else None
