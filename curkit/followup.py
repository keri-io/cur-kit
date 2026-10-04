"""The follow-up message the stop hook sends back when the check result is red."""

from __future__ import annotations

MAX_LOOPS = 25
OUTPUT_LINES = 30
CONFIG = ".cursor/cur-kit.json"
TAIL = (
    "If you're implementing a task, fix this before marking it done. "
    "If this was a spec skill, note it under the task and leave the code alone. "
    "Mark nothing [x] while the suite is red."
)
TIMEOUT_TAIL = (
    "A command timed out, so this is not a test failure and the code is not the problem. "
    f"Raise `timeout` in {CONFIG} if the suite needs longer. Mark nothing [x] while the suite is red."
)
STOP = "If you can't fix it, stop and tell the user."
REPEAT = f"The same failure came back after a change. {STOP}"
REPEAT_UNCHANGED = f"The same failure is still there and nothing in the tree changed. {STOP}"
NO_TASKS_MD = "No tasks.md was found, so no tasks are listed."
NO_CITING_TASK = "No task in tasks.md cites them."


def _bullets(title: str, items: list[str]) -> str:
    return "\n".join([title, *(f"- {item}" for item in items)])


def _failed(outcome: dict) -> bool:
    return bool(outcome.get("timed_out")) or outcome.get("code") != 0


def _command(outcome: dict) -> str:
    lines = [f"$ {outcome.get('command') or outcome.get('name') or ''}"]
    if outcome.get("timed_out"):
        seconds = float(outcome.get("seconds") or 0)
        lines.append(f"Timed out after {seconds:.0f}s. Raise `timeout` in {CONFIG} if the suite needs longer.")
    lines.extend(str(outcome.get("output") or "").splitlines()[-OUTPUT_LINES:])
    return "\n".join(lines)


def _scenarios(result: dict) -> list[str]:
    ids = result.get("ids") or []
    if not ids:
        return []
    tasks = [task.get("text") or task.get("id") or "" for task in result.get("tasks_for_ids") or []]
    head = f"Scenario ids: {', '.join(ids)}"
    if tasks:
        return [_bullets(f"{head}\nTasks that cite them:", tasks)]
    return [f"{head}\n{NO_TASKS_MD if result.get('feature_dir') is None else NO_CITING_TASK}"]


def _sections(result: dict) -> list[str]:
    failing = result.get("failing") or []
    parts = [_bullets("Failing tests:", failing)] if failing else []
    parts.extend(_scenarios(result))
    parts.extend(_command(outcome) for outcome in result.get("outcomes") or [] if _failed(outcome))
    guard = result.get("guard") or []
    if guard:
        parts.append(_bullets("Check-off guard:", guard))
    return parts


def _tail(result: dict) -> str:
    outcomes = result.get("outcomes") or []
    timed_out = any(outcome.get("timed_out") for outcome in outcomes)
    broken = any(_failed(outcome) and not outcome.get("timed_out") for outcome in outcomes)
    return TIMEOUT_TAIL if timed_out and not broken and not result.get("guard") else TAIL


def compose(result: dict, loops: int, repeat: bool) -> str:
    """Failing names, scenario ids with their tasks, each failing command's output, guard messages, then the tail."""
    head = [f"cur-kit: the suite is red ({loops + 1}/{MAX_LOOPS})."]
    if repeat:
        head.append(REPEAT_UNCHANGED if result.get("reused") else REPEAT)
    return "\n\n".join(["\n".join(head), *_sections(result), _tail(result)])
