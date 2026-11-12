"""Cursor hooks: `stop` runs the check after a completed turn, `sessionStart` clears the red latch."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from curkit import check, config, followup, skill_loop
from curkit.hook_latch import judge
from curkit.project_hooks import has_project_stop
from curkit.state import State, failure_print


def project_root(payload: dict) -> Path:
    """CURSOR_PROJECT_DIR when set, else the first workspace root in the payload, else the current directory."""
    env = os.environ.get("CURSOR_PROJECT_DIR", "").strip()
    if env:
        return Path(env)
    roots = payload.get("workspace_roots")
    first = roots[0] if isinstance(roots, list) and roots else None
    return Path(first) if isinstance(first, str) and first.strip() else Path.cwd()


def on_stop(payload: dict, user: bool = False) -> dict:
    """A follow-up while the suite is red, as the latch allows. `{}` otherwise, and on any internal error."""
    try:
        return _stop(payload, user)
    except Exception as exc:  # noqa: BLE001 - a hook must always answer with JSON
        _log_error(payload, exc)
        return {}


def on_session_start(payload: dict) -> dict:
    with contextlib.suppress(Exception):
        State(project_root(payload)).clear_latch()
    return {}


def _stop(payload: dict, user: bool = False) -> dict:
    root = project_root(payload)
    if _quiet(payload, root, user):
        return {}
    result, state = check.run_check(root), State(root)
    if not result["red"]:
        state.clear_latch()
        return skill_loop.after_green(root, payload)
    skill_loop.note_red(root, payload)
    loops = _loops(payload)
    report, latch = judge(state, payload, _failure(result))
    state.save_latch(latch)
    if not report:
        return {}
    return {"followup_message": followup.compose(result, loops, latch["count"] == 2)}


def _quiet(payload: dict, root: Path, user: bool) -> bool:
    if payload.get("status") != "completed" or _loops(payload) >= followup.MAX_LOOPS:
        return True
    if user and has_project_stop(root):
        return True
    return config.load(root) is None


def _loops(payload: dict) -> int:
    try:
        return int(payload.get("loop_count") or 0)
    except (TypeError, ValueError):
        return 0


def _failure(result: dict) -> str:
    if result["ok"] and not result["failing"]:
        return failure_print([f"guard: {line}" for line in result["guard"] or []], "")
    output = "\n".join(outcome["output"] for outcome in result["outcomes"] if check.failed(outcome))
    return failure_print(result["failing"], output)


def _log_error(payload: dict, exc: Exception) -> None:
    with contextlib.suppress(Exception):
        root = project_root(payload)
        if config.load(root) is not None:
            State(root).log({"at": check.now(), "error": f"{type(exc).__name__}: {exc}"})
