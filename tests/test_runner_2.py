"""AC-05: a command over the timeout is killed with its whole process group."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from curkit import runner
from curkit.runner import run_all


def test_ac05_timeout_kills_the_whole_process_group(tmp_path: Path) -> None:
    commands = {
        "test": "sh -c 'sleep 2; touch marker'",
        "lint": "sh -c 'sleep 2; touch nested-marker' & wait",
    }
    start = time.monotonic()
    outcomes = run_all(commands, tmp_path, 0.5)
    returned = time.monotonic() - start
    time.sleep(max(0.0, 2.5 - (time.monotonic() - start)))
    assert [(o.code, o.timed_out) for o in outcomes] == [(None, True), (None, True)]
    assert returned < 1.5 and all(0.4 <= o.seconds < 1.5 for o in outcomes)
    assert not (tmp_path / "marker").exists()
    assert not (tmp_path / "nested-marker").exists(), "a child of the shell outlived the timeout"


def test_ac05_timeout_keeps_the_output_so_far(tmp_path: Path) -> None:
    [outcome] = run_all({"test": "echo started; sleep 5"}, tmp_path, 0.5)
    assert (outcome.code, outcome.timed_out, outcome.output) == (None, True, "started")


def test_ac05_timeout_still_stops_the_command_when_killpg_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(pid: int, sig: int) -> None:
        raise PermissionError("no process groups here")

    monkeypatch.setattr(runner.os, "killpg", refuse)
    start = time.monotonic()
    [outcome] = run_all({"test": "sleep 5"}, tmp_path, 0.3)
    assert time.monotonic() - start < 2
    assert (outcome.code, outcome.timed_out) == (None, True)


def test_ac05_run_all_does_not_wait_for_background_children(tmp_path: Path) -> None:
    start = time.monotonic()
    [outcome] = run_all({"test": "sleep 3 & echo done"}, tmp_path, 10)
    assert time.monotonic() - start < 2, "waited for a background child that kept the output open"
    assert (outcome.code, outcome.timed_out, outcome.output) == (0, False, "done")
