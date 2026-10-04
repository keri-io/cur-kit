"""AC-19: the stop hook stays quiet unless a completed turn left the suite red, then sends a latched follow-up."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from curkit.config import CONFIG_PATH
from curkit.followup import REPEAT, TAIL
from curkit.hooks import on_stop, project_root
from curkit.state import STATE_DIR, State, failure_print
from tests.test_check import FAILING, GREEN, RED, add_speckit, make_project, ran, write

QUIET = [
    {"status": "aborted", "loop_count": 0},
    {"status": "error", "loop_count": 0},
    {"loop_count": 0},
    {"status": "completed", "loop_count": 25},
    {"status": "completed", "loop_count": 40},
]


@pytest.fixture(autouse=True)
def no_cursor_env(monkeypatch):
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def stop_in(root: Path, loops: int = 0) -> dict:
    return on_stop({"status": "completed", "loop_count": loops, "workspace_roots": [str(root)]})


def test_ac19_project_root_prefers_cursor_project_dir_then_workspace_roots_then_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    roots = {"workspace_roots": ["/work/a", "/work/b"]}
    assert project_root(roots) == Path("/work/a")
    for payload in ({}, {"workspace_roots": []}, {"workspace_roots": [7]}, {"workspace_roots": "/work/a"}):
        assert project_root(payload) == tmp_path.resolve()
    monkeypatch.setenv("CURSOR_PROJECT_DIR", "  ")
    assert project_root(roots) == Path("/work/a")
    monkeypatch.setenv("CURSOR_PROJECT_DIR", "/work/env")
    assert project_root(roots) == Path("/work/env")


@pytest.mark.parametrize("payload", QUIET)
def test_ac19_on_stop_is_quiet_unless_a_turn_completed_under_the_loop_limit(tmp_path, monkeypatch, payload):
    root = make_project(tmp_path)
    monkeypatch.setenv("CURSOR_PROJECT_DIR", str(root))
    assert on_stop(payload) == {}
    assert ran(root) == 0


def test_ac19_on_stop_is_quiet_outside_a_cur_kit_project(tmp_path):
    root = make_project(tmp_path)
    (root / CONFIG_PATH).unlink()
    assert stop_in(root) == {}
    assert ran(root) == 0 and not (root / STATE_DIR).exists()
    write(root, CONFIG_PATH, json.dumps({"test": ""}))
    assert stop_in(root) == {} and ran(root) == 0


def test_ac19_red_sends_a_followup_naming_the_failing_ids_and_their_tasks(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    add_speckit(root, monkeypatch)
    message = stop_in(root, loops=3)["followup_message"]
    assert "(4/25)" in message.splitlines()[0] and REPEAT not in message
    for text in (FAILING, "US1/AC2", "T042 Add export per US1/AC2 (missing)", "$ python3 suite.py", "T015 [US2]"):
        assert text in message
    assert message.endswith(TAIL)
    assert State(root).latch() == {"failure": failure_print([FAILING], ""), "count": 1}


def test_ac19_an_unreadable_loop_count_counts_as_zero(tmp_path):
    root = make_project(tmp_path)
    payload = {"status": "completed", "loop_count": ["many"], "workspace_roots": [str(root)]}
    assert "(1/25)" in on_stop(payload)["followup_message"]


def test_ac19_reports_the_same_failure_twice_then_stays_quiet(tmp_path):
    root = make_project(tmp_path)
    replies = []
    for turn in range(4):
        write(root, "notes.md", f"turn {turn}\n")
        replies.append(stop_in(root, loops=turn))
    assert ran(root) == 4
    first, second = replies[0]["followup_message"], replies[1]["followup_message"]
    assert REPEAT not in first and REPEAT in second and "(2/25)" in second
    assert replies[2:] == [{}, {}]


def test_ac19_green_clears_the_latch_and_returns_empty(tmp_path):
    root = make_project(tmp_path)
    assert "followup_message" in stop_in(root)
    write(root, "cases.json", json.dumps(GREEN))
    assert stop_in(root) == {}
    assert not (root / STATE_DIR / "latch.json").exists()
    write(root, "cases.json", json.dumps(RED))
    assert REPEAT not in stop_in(root)["followup_message"]
