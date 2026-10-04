"""AC-05: run_all runs the commands at the same time and records codes, output, and seconds."""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path

import pytest

from curkit.runner import Outcome, run_all


def test_ac05_run_all_runs_commands_at_the_same_time(tmp_path: Path) -> None:
    start = time.monotonic()
    outcomes = run_all({"test": "sleep 1", "lint": "sleep 1"}, tmp_path, 10)
    elapsed = time.monotonic() - start
    assert elapsed < 1.7, f"took {elapsed:.2f}s, so the commands ran one after another"
    assert [o.code for o in outcomes] == [0, 0]
    assert all(0.9 <= o.seconds < 1.7 for o in outcomes)


def test_ac05_run_all_records_exit_codes_in_input_order(tmp_path: Path) -> None:
    outcomes = run_all({"test": "exit 0", "lint": "exit 3", "typecheck": "false"}, tmp_path, 10)
    assert [(o.name, o.command, o.code, o.timed_out) for o in outcomes] == [
        ("test", "exit 0", 0, False),
        ("lint", "exit 3", 3, False),
        ("typecheck", "false", 1, False),
    ]


def test_ac05_run_all_combines_stdout_and_stderr(tmp_path: Path) -> None:
    [outcome] = run_all({"test": "echo out; echo err >&2; echo out2"}, tmp_path, 10)
    assert outcome.output.splitlines() == ["out", "err", "out2"]


def test_ac05_run_all_keeps_the_last_200_lines(tmp_path: Path) -> None:
    [outcome] = run_all({"test": "seq 1 250"}, tmp_path, 10)
    assert outcome.output.splitlines() == [str(n) for n in range(51, 251)]


def test_ac05_run_all_runs_in_the_given_folder(tmp_path: Path) -> None:
    (tmp_path / "marker.txt").write_text("here\n")
    [outcome] = run_all({"test": "cat marker.txt"}, tmp_path, 10)
    assert outcome.output == "here"


def test_ac05_run_all_skips_empty_commands(tmp_path: Path) -> None:
    outcomes = run_all({"test": "true", "lint": "", "typecheck": "   "}, tmp_path, 10)
    assert [o.name for o in outcomes] == ["test"]
    assert run_all({}, tmp_path, 10) == []
    assert run_all({"lint": ""}, tmp_path, 10) == []


def test_ac05_outcome_is_a_frozen_record_with_float_seconds(tmp_path: Path) -> None:
    [outcome] = run_all({"test": "sleep 0.2"}, tmp_path, 10)
    assert isinstance(outcome.seconds, float) and outcome.seconds >= 0.2
    assert outcome == Outcome("test", "sleep 0.2", 0, "", False, outcome.seconds)
    with pytest.raises(dataclasses.FrozenInstanceError):
        outcome.code = 1  # type: ignore[misc]


def test_ac05_run_all_survives_output_that_is_not_utf8(tmp_path: Path) -> None:
    [outcome] = run_all({"test": r"printf '\377ok\n'"}, tmp_path, 10)
    assert outcome.code == 0 and outcome.output == "\ufffdok"
