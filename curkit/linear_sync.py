"""Publish the current Spec Kit repo to its Linear project."""

from __future__ import annotations

import json
import os
from functools import partial
from pathlib import Path

from curkit import check
from curkit.config import CONFIG_PATH, read_object
from curkit.linear_api import (
    HEALTH,
    STATUS,
    graphql,
    issue_nodes,
    label_ids,
    milestones,
    open_team,
    project_id,
    write_doc,
    write_issue,
)
from curkit.linear_board import queue
from curkit.linear_map import DONE, build, repo_key, repo_name
from curkit.state import State

SKILL = Path(".cursor/cur-kit/state/skill.json")


def sync(root: Path, result: dict, transport=None) -> None:
    """Mirror root to Linear. A missing team is a no-op. Other failures are logged."""
    try:
        team = _team(root)
        keyed = bool(os.environ.get("LINEAR_API_KEY", "").strip())
        if team and not keyed:
            queue(root, result, team)
        elif team:
            _push(root, result, transport)
    except Exception as exc:  # noqa: BLE001 - the stop hook must still answer
        State(root).log({"at": check.now(), "error": f"Linear: {type(exc).__name__}: {exc}"})


def _push(root: Path, result: dict, transport) -> None:
    team = _team(root)
    if not team or not os.environ.get("LINEAR_API_KEY", "").strip():
        return
    record = _json(root / SKILL)
    wanted = build(root, record, bool(result.get("red")))
    run = partial(graphql, transport=transport)
    ctx = open_team(run, team)
    key = repo_key(root)
    project = project_id(run, (ctx["id"], repo_name(key, root), key))
    names = [label for card in wanted for label in card.labels]
    found = issue_nodes(run, project)
    _place(run, (wanted, found, ctx, project, milestones(run, project), label_ids(run, ctx["id"], names)))
    kind = "completed" if _confirmed(record, result) else "started"
    status = _state(ctx["statuses"], kind)
    if status:
        run(STATUS, {"id": project, "input": {"statusId": status}})
    health = "atRisk" if result.get("red") else "onTrack"
    note = "cur-kit: suite red" if result.get("red") else "cur-kit: suite on track"
    run(HEALTH, {"input": {"projectId": project, "health": health, "body": note}})


def _team(root: Path) -> str:
    block = (read_object(root / CONFIG_PATH) or {}).get("linear")
    team = block.get("team") if isinstance(block, dict) else ""
    return team.strip() if isinstance(team, str) else ""


def _place(run, bundle: tuple) -> None:
    wanted, found, ctx, project, stones, labels = bundle
    grouped = _grouped(found)
    keys = {card.key for card in wanted}
    for card in wanted:
        url = write_doc(run, (project, card.title, card.document))
        nodes = grouped.get(card.key, [])
        ident = nodes[0]["id"] if nodes else ""
        payload = _payload(card, (ident, ctx, project, stones, labels))
        if url:
            payload["input"]["description"] = f"{card.body}\n\n{url}"
        saved = write_issue(run, payload)
        for extra in nodes[1:]:
            write_issue(run, {"id": extra["id"], "input": {"cycleId": None}, "duplicate": saved})
    _cancel(run, (grouped, keys, ctx["states"]))


def _payload(card, setup: tuple) -> dict:
    ident, ctx, project, stones, labels = setup
    data = {
        "title": f"[{card.key}] {card.title}"[:255],
        "description": card.body,
        "stateId": _state(ctx["states"], card.status),
        "priority": card.priority,
        "projectId": project,
        "labelIds": [labels[name] for name in card.labels if name in labels],
        "cycleId": ctx.get("cycle") if card.cycle else None,
    }
    if stones.get(card.milestone):
        data["projectMilestoneId"] = stones[card.milestone]
    if not ident:
        data["teamId"] = ctx["id"]
    return {"id": ident, "input": data}


def _grouped(nodes: list[dict]) -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {}
    ordered = sorted(nodes, key=lambda item: item.get("createdAt") or "")
    for node in ordered:
        title = node.get("title") or ""
        key = title[1:title.find("]")] if title.startswith("[") and "]" in title else ""
        if key:
            found.setdefault(key, []).append(node)
    return found


def _cancel(run, facts: tuple) -> None:
    grouped, keys, states = facts
    state = _state(states, "Canceled")
    for key, nodes in grouped.items():
        task = key.startswith("T") and key[1:].isdigit()
        if task and key not in keys:
            write_issue(run, {"id": nodes[0]["id"], "input": {"stateId": state, "cycleId": None}})


def _state(states: list[dict], status: str) -> str:
    named = [node for node in states if str(node.get("name", "")).lower() == status.lower()]
    if named:
        return named[0]["id"]
    kinds = {
        "Backlog": "backlog", "Todo": "unstarted", "In Progress": "started", "In Review": "started",
        "Done": "completed", "Canceled": "canceled", "started": "started", "completed": "completed",
    }
    pool = [node for node in states if node.get("type") == kinds.get(status, status)]
    review = [node for node in pool if "review" in str(node.get("name", "")).lower()]
    plain = [node for node in pool if node not in review]
    pick = review or pool if status == "In Review" else plain or pool
    if not pick:
        raise RuntimeError(status)
    return pick[0]["id"]


def _confirmed(record: dict, result: dict) -> bool:
    if result.get("red"):
        return False
    prompt = record.get("prompt")
    text = prompt.lower() if isinstance(prompt, str) else ""
    named = "speckit-converge" in text or "speckit.converge" in text
    body = record.get("response")
    words = body.lower() if isinstance(body, str) else ""
    return named and any(phrase in words for phrase in DONE)


def _json(path: Path) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}
