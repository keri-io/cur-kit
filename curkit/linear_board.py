"""Queue a Linear board for the Cursor Linear MCP. No API key is required."""

from __future__ import annotations

import json
from pathlib import Path

from curkit.linear_map import DONE, build, repo_key, repo_name

SKILL = Path(".cursor/cur-kit/state/skill.json")
BOARD = Path(".cursor/cur-kit/state/linear-board.json")
MILESTONES = ["Specify", "Plan", "Tasks", "Implement", "Converge"]


def queue(root: Path, result: dict, team: str) -> None:
    """Write the board the next Cursor turn applies when the Linear MCP is connected."""
    record = _read(root / SKILL)
    cards = build(root, record, bool(result.get("red")))
    origin = repo_key(root)
    path = root / BOARD
    facts = (team, origin, repo_name(origin, root), record, result, cards, _read(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_board(facts), indent=2) + "\n", encoding="utf-8")


def _board(facts: tuple) -> dict:
    team, origin, name, record, result, cards, prior = facts
    state = "completed" if _done(record, result) else "started"
    health = "atRisk" if result.get("red") else "onTrack"
    note = "cur-kit: suite red" if result.get("red") else "cur-kit: suite on track"
    return {
        "pending": True,
        "via": "linear-mcp",
        "team": team,
        "project": {"name": name, "summary": f"cur-kit:{origin}", "state": state},
        "milestones": MILESTONES,
        "health": health,
        "note": note,
        "removedTasks": _removed(prior, cards),
        "issues": [_issue(card) for card in cards],
    }


def _issue(card) -> dict:
    return {
        "key": card.key,
        "title": f"[{card.key}] {card.title}"[:255],
        "description": card.body,
        "document": card.document,
        "state": card.status,
        "priority": card.priority,
        "milestone": card.milestone,
        "labels": list(card.labels),
        "cycle": card.cycle,
    }


def _removed(prior: dict, cards: list) -> list[str]:
    current = {card.key for card in cards}
    found = []
    for item in prior.get("issues") or []:
        key = item.get("key") if isinstance(item, dict) else ""
        task = isinstance(key, str) and key.startswith("T") and key[1:].isdigit()
        if task and key not in current:
            found.append(key)
    return found


def _done(record: dict, result: dict) -> bool:
    if result.get("red"):
        return False
    prompt = record.get("prompt")
    text = prompt.lower() if isinstance(prompt, str) else ""
    named = "speckit-converge" in text or "speckit.converge" in text
    body = record.get("response")
    words = body.lower() if isinstance(body, str) else ""
    return named and any(phrase in words for phrase in DONE)


def _read(path: Path) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}
