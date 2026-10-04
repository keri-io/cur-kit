"""AC-19 and AC-20: guard-only and timed-out follow-ups, internal errors, and the session start hook."""

from __future__ import annotations

import json

import pytest

from curkit import check
from curkit.followup import REPEAT, REPEAT_UNCHANGED, TIMEOUT_TAIL
from curkit.hooks import on_session_start, on_stop
from curkit.state import STATE_DIR, State, failure_print
from tests.test_check import CONFIG, FAILING, GREEN, PASSING, RED, add_speckit, make_project, write
from tests.test_hooks import stop_in

US2_GUARD = "T015 [US2] is checked, but no passing test cites US2."


@pytest.fixture(autouse=True)
def no_cursor_env(monkeypatch):
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def explode(*args: object) -> dict:
    raise RuntimeError("disk on fire")


def test_ac19_a_guard_only_red_reports_the_guard_messages(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    add_speckit(root, monkeypatch)
    message = stop_in(root)["followup_message"]
    assert US2_GUARD in message and "$ python3" not in message
    assert State(root).latch() == {"failure": failure_print([f"guard: {US2_GUARD}"], ""), "count": 1}


def test_r3_a_zero_exit_with_junit_failures_reports_the_failing_names(tmp_path):
    root = make_project(tmp_path, {"test": f"{CONFIG['test']} || true"})
    assert FAILING in stop_in(root)["followup_message"]
    assert State(root).latch() == {"failure": failure_print([FAILING], ""), "count": 1}


def test_ac19_a_timed_out_suite_says_so_instead_of_blaming_the_code(tmp_path):
    root = make_project(tmp_path, {"test": "sleep 5", "junit": "", "timeout": 0.3})
    message = stop_in(root)["followup_message"]
    assert "Timed out after" in message and "`timeout` in .cursor/cur-kit.json" in message
    assert message.endswith(TIMEOUT_TAIL)


def test_ac19_a_different_failure_is_reported_again(tmp_path):
    root = make_project(tmp_path)
    assert "followup_message" in stop_in(root)
    assert REPEAT_UNCHANGED in stop_in(root)["followup_message"]
    assert stop_in(root) == {}
    write(root, "cases.json", json.dumps({**RED, PASSING: "fail"}))
    message = stop_in(root)["followup_message"]
    assert REPEAT not in message and REPEAT_UNCHANGED not in message
    assert State(root).latch()["count"] == 1


def test_ac19_on_stop_returns_empty_and_logs_the_error_when_the_check_raises(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(check, "run_check", explode)
    assert stop_in(root) == {}
    [entry] = [json.loads(line) for line in (root / STATE_DIR / "runs.jsonl").read_text().splitlines()]
    assert set(entry) == {"at", "error"} and "disk on fire" in entry["error"]


def test_ac19_on_stop_returns_empty_when_the_error_cannot_be_logged(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    write(root, STATE_DIR, "a file where the state folder goes\n")
    monkeypatch.setattr(check, "run_check", explode)
    assert stop_in(root) == {}
    assert on_stop("not a payload") == {}


def test_ac20_on_session_start_clears_the_latch_so_a_new_chat_hears_the_failure_again(tmp_path):
    root = make_project(tmp_path)
    assert [bool(stop_in(root)) for _ in range(3)] == [True, True, False]
    assert on_session_start({"workspace_roots": [str(root)]}) == {}
    assert not (root / STATE_DIR / "latch.json").exists()
    assert REPEAT not in stop_in(root)["followup_message"]


def test_ac20_on_session_start_returns_empty_on_bad_input_or_errors(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    (root / STATE_DIR / "latch.json").mkdir(parents=True)
    assert on_session_start({"workspace_roots": [str(root)]}) == {}
    assert on_session_start("not a payload") == {}
    monkeypatch.chdir(tmp_path)
    assert on_session_start({}) == {}
