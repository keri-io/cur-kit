"""AC-07: compose on timeouts, repeats, and sparse results."""

from __future__ import annotations

from curkit.followup import TAIL, compose
from tests.test_followup import _outcome, _result


def test_ac07_timeout_names_the_timeout_key_and_does_not_ask_for_a_code_fix():
    timed_out = _outcome(code=None, timed_out=True, seconds=300.4, output="collecting ...")
    message = compose(_result(outcomes=[timed_out], failing=[], ids=[], tasks_for_ids=[], guard=None), 0, False)
    assert "timed out" in message.lower()
    assert "`timeout`" in message and ".cursor/cur-kit.json" in message
    assert "fix" not in message.lower()
    assert not message.endswith(TAIL)
    assert "Mark nothing [x] while the suite is red." in message


def test_ac07_timeout_beside_a_real_failure_keeps_the_tail():
    outcomes = [_outcome(code=None, timed_out=True, seconds=300.0), _outcome(name="lint", command="ruff check .")]
    message = compose(_result(outcomes=outcomes), 0, False)
    assert "timed out" in message.lower() and "`timeout`" in message
    assert message.endswith(TAIL)


def test_ac07_repeat_says_the_failure_came_back_and_when_to_stop():
    message = compose(_result(), 1, True)
    assert "came back after a change" in message
    assert "stop and tell the user" in message
    assert "(2/25)" in message
    assert "came back" not in compose(_result(), 1, False)


def test_ac07_r12_repeat_on_a_reused_result_says_nothing_in_the_tree_changed():
    message = compose(_result(reused=True), 1, True)
    assert "The same failure is still there and nothing in the tree changed." in message
    assert "came back after a change" not in message
    assert "stop and tell the user" in message
    assert "came back after a change" in compose(_result(reused=False), 1, True)
    assert "still there" not in compose(_result(reused=True), 1, False)


def test_ac07_r12_null_feature_dir_says_no_tasks_md_was_found():
    message = compose(_result(feature_dir=None, tasks_for_ids=[]), 0, False)
    assert "Scenario ids: US1/AC2, FR-003" in message
    assert "No tasks.md was found, so no tasks are listed." in message
    assert "cites them" not in message
    with_feature = compose(_result(tasks_for_ids=[]), 0, False)
    assert "No task in tasks.md cites them." in with_feature
    assert "No tasks.md was found" not in with_feature


def test_ac07_tolerates_a_sparse_result():
    message = compose({"outcomes": [{"name": "test", "command": "bun test", "code": 2, "output": ""}]}, 0, False)
    assert "$ bun test" in message
    assert message.endswith(TAIL)
    assert compose({}, 0, False).endswith(TAIL)
