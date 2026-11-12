"""Decide the next implement or converge command from the saved turn and tasks.md."""

from __future__ import annotations

import re
from pathlib import Path

from curkit.speckit import tasks_path
from curkit.tasks import open_tasks, parse_tasks

CONVERGE = "/speckit-converge"
IMPLEMENT = "/speckit-implement"
DONE = ("no further implement", "implementation is complete")
NAMED = ("speckit-implement", "speckit.implement")
NEGATED = re.compile(r"\b(?:not|never)\b(?:\s+\w+){0,3}\s+converged\b|\b\w+n't(?:\s+\w+){0,3}\s+converged\b")


def next_command(root: Path, record: dict, kind: str) -> str:
    """`/speckit-converge` after implement, `/speckit-implement` when converge still has work."""
    owed = bool(record.get("owed")) and kind != "converge"
    if kind == "implement" or owed:
        return CONVERGE
    if kind == "converge" and _again(root, record):
        return IMPLEMENT
    return ""


def snapshot(root: Path, record: dict) -> None:
    """Remember open task ids at the start of a converge turn."""
    record["open_ids"] = sorted(_open_ids(root))


def _again(root: Path, record: dict) -> bool:
    text = record.get("response")
    body = text.lower() if isinstance(text, str) else ""
    if _fresh(root, record):
        return True
    return _names_implement(body) and not _finished(body)


def _finished(body: str) -> bool:
    kept = NEGATED.sub(" ", body)
    if "converged" in kept:
        return True
    return any(phrase in body for phrase in DONE)


def _names_implement(body: str) -> bool:
    return any(token in body for token in NAMED)


def _fresh(root: Path, record: dict) -> bool:
    seen = record.get("open_ids")
    if not isinstance(seen, list):
        return False
    prior = {item for item in seen if isinstance(item, str)}
    return bool(_open_ids(root) - prior)


def _open_ids(root: Path) -> set[str]:
    path = tasks_path(root)
    if path is None:
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {task.id for task in open_tasks(parse_tasks(text))}
