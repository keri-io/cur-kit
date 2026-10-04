"""AC-22: a red suite in a Spec Kit project, seen through `cur-kit hook stop` and `cur-kit check --json`."""

from __future__ import annotations

import json

TAIL = (
    "If you're implementing a task, fix this before marking it done. "
    "If this was a spec skill, note it under the task and leave the code alone. "
    "Mark nothing [x] while the suite is red."
)
REPEAT = "same failure"
T014 = "T014 [US1] Implement login redirect in src/auth.py"
FAILING = ["tests.test_auth::test_US1_AC2_redirects"]
EXIT_0 = "python3 suite.py || true"


def test_ac22_stop_names_the_failing_scenario_and_task(project):
    message = project.stop()["followup_message"]
    assert "test_US1_AC2_redirects" in message and "US1/AC2" in message
    assert T014 in message and "T015" not in message
    assert "(1/25)" in message and REPEAT not in message
    assert message.endswith(TAIL)


def test_ac22_the_same_failure_gets_one_more_followup_then_empty(project):
    first, second = project.stop(loop_count=0), project.stop(loop_count=1)
    assert REPEAT not in first["followup_message"]
    assert REPEAT in second["followup_message"] and "(2/25)" in second["followup_message"]
    assert "US1/AC2" in second["followup_message"] and T014 in second["followup_message"]
    assert project.stop(loop_count=2) == {}
    assert project.stop(loop_count=0) == {}


def test_ac22_after_the_fix_stop_returns_empty_and_the_latch_resets(project):
    assert [bool(project.stop(loop_count=n)) for n in range(3)] == [True, True, False]
    project.fix()
    assert project.stop() == {}
    assert project.check()["red"] is False
    # A spent latch also returns {}. Only a cleared one reports the next failure again.
    (project.root / "fixed").unlink()
    message = project.stop()["followup_message"]
    assert "US1/AC2" in message and REPEAT not in message


def test_ac22_check_json_reports_red_and_open_and_exits_0_while_red(project):
    project.stop()
    done = project.run("check", "--json")
    assert done.returncode == 0, done.stderr
    before = json.loads(done.stdout)
    assert (before["configured"], before["ok"], before["red"], before["reused"]) == (True, False, True, True)
    assert (before["open"], before["open_tasks"], before["guard"]) == (2, ["T014", "T015"], [])
    assert (before["failing"], before["ids"], before["unplanned"]) == (FAILING, ["US1/AC2"], [])
    assert before["tasks_for_ids"] == [{"id": "T014", "text": T014}]
    assert str(before["feature_dir"]).endswith("specs/001-login")
    project.fix()
    project.tick("T014")
    after = project.check()
    assert (after["ok"], after["red"], after["reused"], after["guard"]) == (True, False, False, [])
    assert (after["open"], after["open_tasks"], after["failing"]) == (1, ["T015"], [])
    assert after["unplanned"] == ["fixed"]


def test_r3_a_suite_that_exits_0_with_a_failing_report_is_red_and_followed_up(project):
    project.configure(test=EXIT_0)
    message = project.stop()["followup_message"]
    assert "test_US1_AC2_redirects" in message and "US1/AC2" in message and T014 in message
    result = project.check()
    assert (result["red"], result["failing"]) == (True, FAILING)
    assert [outcome["code"] for outcome in result["outcomes"]] == [0]


def test_r3_a_new_failure_while_the_suite_exits_0_is_not_a_repeat(project):
    project.configure(test=EXIT_0)
    assert REPEAT not in project.stop()["followup_message"]
    suite = project.root / "suite.py"
    text = suite.read_text(encoding="utf-8")
    suite.write_text(text.replace("US1_AC2_redirects", "US2_AC1_logs_out"), encoding="utf-8")
    message = project.stop()["followup_message"]
    assert "test_US2_AC1_logs_out" in message and "T015 [US2] Add logout in src/session.py" in message
    assert REPEAT not in message
