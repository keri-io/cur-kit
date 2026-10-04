"""AC-19 and AC-20 through the CLI: when `cur-kit hook stop` stays quiet, and what resets the red latch."""

from __future__ import annotations

import pytest

REPEAT = "same failure"
GUARD = "T015 [US2] is checked, but no passing test cites US2."
MALFORMED = ["", "not json", "null", "[1, 2]", '{"status": "completed", "loop_count": 0']


def test_ac19_stop_outside_a_cur_kit_project_returns_empty(kit):
    assert kit.stop() == {}
    assert list(kit.root.iterdir()) == []


def test_ac19_stop_ignores_a_project_with_only_bootstrap_json(project):
    cursor = project.root / ".cursor"
    (cursor / "cur-kit.json").rename(cursor / "bootstrap.json")
    assert project.stop() == {}
    assert not (project.root / "report.xml").exists()
    assert not (cursor / "cur-kit").exists()


@pytest.mark.parametrize("status", ["aborted", "error"])
def test_ac19_stop_returns_empty_when_the_turn_did_not_complete(project, status):
    assert project.stop(status=status) == {}
    assert REPEAT not in project.stop()["followup_message"]


def test_ac19_stop_returns_empty_at_the_loop_limit(project):
    assert project.stop(loop_count=25) == {}
    message = project.stop(loop_count=24)["followup_message"]
    assert "(25/25)" in message and REPEAT not in message


def test_ac19_stop_reports_the_check_off_guard_while_the_suite_passes(project):
    project.fix()
    project.tick("T015")
    assert GUARD in project.stop()["followup_message"]
    result = project.check()
    assert (result["ok"], result["red"], result["guard"]) == (True, True, [GUARD])


def test_ac20_session_start_clears_the_latch(project):
    assert [bool(project.stop(loop_count=n)) for n in range(3)] == [True, True, False]
    assert project.hook("session-start", '{"hook_event_name": "sessionStart"}') == {}
    message = project.stop()["followup_message"]
    assert "US1/AC2" in message and REPEAT not in message


@pytest.mark.parametrize("event", ["stop", "session-start"])
@pytest.mark.parametrize("stdin", MALFORMED)
def test_ac19_ac20_hooks_print_json_and_exit_0_on_malformed_stdin(project, event, stdin):
    assert project.hook(event, stdin) == {}
