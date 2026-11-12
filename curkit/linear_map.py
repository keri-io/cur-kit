"""Map a Spec Kit repo onto Linear cards. Files stay the source of truth."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from curkit.linear_files import feature, marks, text
from curkit.tasks import parse_tasks

DONE = ("converged", "no further implement", "implementation is complete")
DOCS = (
    ("constitution", "Constitution", "root", ".specify/memory/constitution.md", "Specify", "constitution"),
    ("specification", "Specification", "feature", "spec.md", "Specify", "specify"),
    ("plan", "Plan", "feature", "plan.md", "Plan", "plan"),
    ("research", "Research", "feature", "research.md", "Plan", "research"),
)
ACTIVE = ("In Progress", "In Review")
NAMES = ("constitution", "checklist", "specify", "implement", "converge", "tasks", "plan")


@dataclass(frozen=True)
class Turn:
    current: str
    nxt: str
    done: bool


@dataclass(frozen=True)
class Card:
    key: str
    title: str
    body: str
    document: str
    status: str
    priority: int
    milestone: str
    labels: tuple[str, ...]
    cycle: bool


def build(root: Path, record: dict, red: bool) -> list[Card]:
    """Cards for one stop. `record` is skill.json and `red` is the suite."""
    current = _skill(record.get("prompt"))
    nxt = _next((current, bool(record.get("owed")), record.get("response"), red))
    body = record.get("response")
    words = body.lower() if isinstance(body, str) else ""
    finished = (not red) and current == "converge" and any(phrase in words for phrase in DONE)
    turn = Turn(current, nxt, finished)
    folder = feature(root)
    show = body if isinstance(body, str) and current == "converge" else ""
    status = _status(turn, ("converge", bool(show), ""))
    cards = _docs(root, folder, turn)
    cards.extend(_tasks(folder, turn))
    if show or status == "In Progress":
        cards.append(_make((
            "findings", "Convergence findings", show, status,
            _priority(show, "converge", None), "Converge", ("convergence",),
        )))
    return cards


def repo_key(root: Path) -> str:
    """origin URL, or the folder name when the repo has no remote."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return root.name
    return done.stdout.strip() or root.name


def repo_name(key: str, root: Path) -> str:
    tail = key.rstrip("/").split("/")[-1].split(":")[-1]
    return tail.removesuffix(".git") or root.name


def _docs(root: Path, folder: Path | None, turn: Turn) -> list[Card]:
    cards = []
    for key, title, kind, rel, milestone, skill in DOCS:
        path = root / rel if kind == "root" else (folder / rel if folder else None)
        body = text(path)
        status = _status(turn, (skill, bool(body), ""))
        rank = _priority(body, skill, None)
        cards.append(_make((key, title, body, status, rank, milestone, ())))
    base = folder / "checklists" if folder else None
    paths = sorted(base.glob("*.md")) if base and base.is_dir() else []
    for path in paths:
        body = text(path)
        status = _status(turn, ("checklist", bool(body), ""))
        label = f"Checklist {path.stem}"
        cards.append(_make((f"checklist:{path.stem}", label, body, status, 4, "Tasks", ())))
    return cards


def _tasks(folder: Path | None, turn: Turn) -> list[Card]:
    body = text(folder / "tasks.md") if folder else ""
    noted = marks(body)
    cards = []
    for task in parse_tasks(body):
        mark, converge = noted.get(task.id, (" ", False))
        status = _status(turn, ("task", True, mark))
        labels = tuple(item for item in (task.story, "convergence" if converge else "") if item)
        milestone = "Converge" if converge else "Implement"
        rank = _priority(task.text, "task", task.story)
        cards.append(_make((task.id, task.text, "", status, rank, milestone, labels)))
    return cards


def _make(fields: tuple) -> Card:
    key, title, document, status, priority, milestone, labels = fields
    line = document.splitlines()[0] if document else title
    return Card(key, title, line[:240], document, status, priority, milestone, labels, status in ACTIVE)


def _status(turn: Turn, spec: tuple) -> str:
    skill, exists, mark = spec
    if mark and mark not in (" ", "x", "X"):
        return "Canceled"
    checked = mark in ("x", "X")
    if turn.done and (checked or (not mark and exists)):
        return "Done"
    if checked:
        return "In Review"
    if mark and (turn.current == "implement" or turn.nxt == "implement"):
        return "In Progress"
    if mark:
        return "Todo"
    if skill == turn.nxt or (skill == turn.current and not exists):
        return "In Progress"
    return "In Review" if exists else "Backlog"


def _priority(body: str, kind: str, story: str | None) -> int:
    low = body.lower()
    if kind in ("research", "checklist"):
        return 4
    if kind == "constitution":
        return 3
    if "critical" in low or "constitution breach" in low:
        return 1
    if story == "US1" or " high" in f" {low}":
        return 2
    if " low" in f" {low}":
        return 4
    return 3


def _skill(prompt: object) -> str:
    words = prompt.lower() if isinstance(prompt, str) else ""
    picked = []
    for line in words.splitlines():
        text = line.strip().strip("`").split()[:1]
        slash = [name for name in NAMES if text == [f"/speckit-{name}"]]
        dot = [name for name in NAMES if text == [f"/speckit.{name}"]]
        picked.extend((slash or dot)[:1])
    if picked:
        return picked[-1]
    pairs = [(name, f"speckit-{name}") for name in NAMES]
    pairs += [(name, f"speckit.{name}") for name in NAMES]
    found = [(words.find(token), name) for name, token in pairs if token in words]
    return min(found)[1] if found else ""


def _next(facts: tuple) -> str:
    name, owed, response, red = facts
    body = response.lower() if isinstance(response, str) else ""
    if red:
        return ""
    if name == "implement" or (owed and name != "converge"):
        return "converge"
    blocked = any(phrase in body for phrase in DONE)
    named = "speckit-implement" in body or "speckit.implement" in body
    return "implement" if name == "converge" and named and not blocked else ""
