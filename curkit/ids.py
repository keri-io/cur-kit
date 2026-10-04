"""Scenario keys (FR-###, SC-###, USn, USn/ACn) found in prose and in test names."""

from __future__ import annotations

import re

_EDGE = r"(?<![A-Za-z0-9])"
_END = r"(?![A-Za-z0-9])"
_REQ = r"(?P<req>FR|SC)[-_]?(?P<num>\d{3})"
_STORY = r"(?P<story>US\d+)(?:[-_/ ]?(?P<ac>AC\d+))?"
# Spec Kit's spec headings ("User Story N") and converge's shorthand ("AC1", "acceptance scenario 1").
_LONG = re.compile(
    r"(?<![A-Za-z0-9])user[- ]story[- ](?P<n>\d+)"
    r"(?:[- ,]+(?:ac[- ]?(?P<ac>\d+)|acceptance[- ]scenario[- ](?P<scene>\d+)))?"
    r"(?![A-Za-z0-9])",
    re.IGNORECASE,
)
KEY = re.compile(f"{_EDGE}(?:{_REQ}|{_STORY}){_END}", re.IGNORECASE)
STORY = re.compile(r"(US\d+)(?:/AC\d+)?")


def _canonical(match: re.Match[str]) -> str:
    if match["req"]:
        return f"{match['req'].upper()}-{match['num']}"
    story = match["story"].upper()
    return f"{story}/{match['ac'].upper()}" if match["ac"] else story


def _long_key(match: re.Match[str]) -> str:
    number = match["ac"] or match["scene"]
    story = f"US{match['n']}"
    return f"{story}/AC{number}" if number else story


def _hits(text: str) -> list[tuple[int, str]]:
    short = [(match.start(), _canonical(match)) for match in KEY.finditer(text)]
    long = [(match.start(), _long_key(match)) for match in _LONG.finditer(text)]
    return sorted([*short, *long])


def keys_in(text: str) -> list[str]:
    """Canonical keys in text, unique, in first-seen order."""
    return list(dict.fromkeys(key for _, key in _hits(text)))


def story_of(key: str) -> str | None:
    """The story a canonical key belongs to: US1/AC2 -> US1, US3 -> US3, FR-003 -> None."""
    match = STORY.fullmatch(key)
    return match[1] if match else None
