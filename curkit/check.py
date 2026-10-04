"""`cur-kit check`: run the project's commands, or reuse the last run when the tree is unchanged, then read the plan."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from curkit import config, guard, ids, junit, runner, speckit, tree
from curkit.state import State
from curkit.tasks import Task, open_tasks, parse_tasks, tasks_citing

NOT_PLANNED = (".cursor/", ".specify/", "specs/")
RUN_KEYS = ("ok", "key", "outcomes", "cases", "failing", "ids")
NO_RUN = {"ok": True, "key": None, "outcomes": [], "cases": None, "failing": [], "ids": []}
# The workflow passes the whole check stdout to implement as one argument, and Linux caps one argument at 128 KiB.
OUTPUT_LINES, OUTPUT_CHARS, MAX_FAILING = 30, 4000, 50
FAILURE_LINE = re.compile(r"fail|error", re.IGNORECASE)


class Plan(NamedTuple):
    feature_dir: str | None
    tasks: list[Task]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def failed(outcome: dict) -> bool:
    return bool(outcome.get("timed_out")) or outcome.get("code") != 0


def run_check(root: Path) -> dict:
    """The check result for root, as described in docs/spec.md. Every configured call is logged."""
    started = time.monotonic()
    cfg = config.load(root)
    if cfg is None or not cfg.test:
        return _result(None, _plan(root), False)
    state = State(root)
    salt = json.dumps([config.commands(cfg), cfg.junit], sort_keys=True)
    stored = _stored(state, tree.fingerprint(root, salt)) if cfg.cache else None
    run = stored or _record(*_execute(root, cfg, salt))
    if stored is None:
        state.save_last(run)
    plan = _plan(root)
    result = {**_result(run, plan, stored is not None), "unplanned": _unplanned(root, plan.tasks, cfg.junit)}
    seconds = round(time.monotonic() - started, 3)
    state.log({"at": now(), "key": result["key"], "reused": result["reused"], "ok": result["ok"],
               "red": result["red"], "seconds": seconds, "ids": result["ids"], "open": result["open"]})
    return result


def _execute(root: Path, cfg: config.Config, salt: str) -> tuple[list[dict], list[junit.Case] | None, str | None]:
    report = root / cfg.junit if cfg.junit else None
    before = tree.tracked_print(root, salt)
    if report:
        report.unlink(missing_ok=True)
    outcomes = [asdict(outcome) for outcome in runner.run_all(config.commands(cfg), root, cfg.timeout)]
    # The report this run wrote is part of the next run's tree, so the key is taken after the run.
    # A tracked edit during the run means this result may be stale, so it gets no key.
    key = tree.fingerprint(root, salt) if tree.tracked_print(root, salt) == before else None
    return outcomes, junit.read_junit(report) if report else None, key


def _record(outcomes: list[dict], cases: list[junit.Case] | None, key: str | None) -> dict:
    """The stored run. Without JUnit, ids come from the failure and error lines of the failing commands."""
    bad = [outcome for outcome in outcomes if failed(outcome)]
    failing = [case.name for case in cases or [] if case.failed]
    lines = [line for outcome in bad for line in outcome["output"].splitlines() if FAILURE_LINE.search(line)]
    return {
        "ok": not bad,
        "key": key,
        "outcomes": [
            {**outcome, "output": "\n".join(outcome["output"].splitlines()[-OUTPUT_LINES:])[-OUTPUT_CHARS:]}
            for outcome in outcomes
        ],
        "cases": None if cases is None else [asdict(case) for case in cases],
        "failing": failing[:MAX_FAILING],
        "ids": ids.keys_in("\n".join(failing if cases is not None else lines)),
    }


def _stored(state: State, key: str | None) -> dict | None:
    last = state.last()
    if key is None or last is None or last.get("key") != key or not all(name in last for name in RUN_KEYS):
        return None
    try:
        _cases(last["cases"])
    except TypeError:
        return None
    return last


def _cases(data: list[dict] | None) -> list[junit.Case] | None:
    return None if data is None else [junit.Case(**item) for item in data]


def _result(run: dict | None, plan: Plan, reused: bool) -> dict:
    data = run or NO_RUN
    still_open = open_tasks(plan.tasks)
    checked = guard.violations(plan.tasks, _cases(data["cases"]))
    return {
        "configured": run is not None, "ok": data["ok"],
        "red": not data["ok"] or bool(data["failing"]) or bool(checked), "reused": reused,
        "key": data["key"], "outcomes": data["outcomes"], "failing": data["failing"], "ids": data["ids"],
        "tasks_for_ids": [{"id": task.id, "text": task.text} for task in tasks_citing(plan.tasks, data["ids"])],
        "open": len(still_open), "open_tasks": [task.id for task in still_open], "guard": checked,
        "unplanned": [], "feature_dir": plan.feature_dir,
    }


def _plan(root: Path) -> Plan:
    """The feature folder and its tasks. The folder is resolved once, since that may run check-prerequisites."""
    folder = speckit.feature_dir(root)
    path = folder / "tasks.md" if folder else None
    found = parse_tasks(path.read_text(encoding="utf-8", errors="replace")) if path and path.is_file() else []
    if folder is None:
        return Plan(None, found)
    real, base = folder.resolve(), root.resolve()
    return Plan(real.relative_to(base).as_posix() if real.is_relative_to(base) else str(folder), found)


def _unplanned(root: Path, found: list[Task], report: str) -> list[str]:
    planned = {path for task in found for path in task.paths}
    skip = (*NOT_PLANNED, *(path.rstrip("/") + "/" for path in planned))
    left_out = planned | ({Path(os.path.normpath(report)).as_posix()} if report else set())
    return [name for name in tree.changed_files(root) if name not in left_out and not name.startswith(skip)]
