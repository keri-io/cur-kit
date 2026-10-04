"""AC-07: compose the follow-up message from a check result (timeouts and repeat are in test_followup_2.py)."""

from __future__ import annotations

from curkit.followup import TAIL, compose

SPEC_TAIL = (
    "If you're implementing a task, fix this before marking it done. "
    "If this was a spec skill, note it under the task and leave the code alone. "
    "Mark nothing [x] while the suite is red."
)


def _outcome(**overrides: object) -> dict:
    base = {"name": "test", "command": "pytest -q", "code": 1, "timed_out": False, "seconds": 1.2}
    base["output"] = "\n".join(f"line {i:02d}" for i in range(40))
    return {**base, **overrides}


def _result(**overrides: object) -> dict:
    base = {
        "configured": True, "ok": False, "red": True, "reused": False, "key": "abc123",
        "outcomes": [_outcome(), _outcome(name="lint", command="ruff check .", code=0, output="All checks passed!")],
        "failing": ["tests/test_auth.py::test_US1_AC2_redirects", "tests/test_auth.py::test_fr_003_validates"],
        "ids": ["US1/AC2", "FR-003"],
        "tasks_for_ids": [
            {"id": "T014", "text": "T014 [US1] Implement login in src/auth.py"},
            {"id": "T043", "text": "T043 Validate email format per FR-003 (partial)"},
        ],
        "open": 2, "open_tasks": ["T042", "T043"],
        "guard": ["T015 [US2] is checked, but no passing test cites US2."],
        "unplanned": ["src/extra.py"], "feature_dir": "specs/001-login",
    }
    return {**base, **overrides}


def test_ac07_header_counts_loops_out_of_25():
    assert "(1/25)" in compose(_result(), 0, False).splitlines()[0]
    assert "(4/25)" in compose(_result(), 3, False).splitlines()[0]


def test_ac07_lists_failing_names_and_ids_with_their_tasks():
    message = compose(_result(), 0, False)
    assert "tests/test_auth.py::test_US1_AC2_redirects" in message
    assert "tests/test_auth.py::test_fr_003_validates" in message
    assert "US1/AC2" in message and "FR-003" in message
    assert "T014 [US1] Implement login in src/auth.py" in message
    assert "T043 Validate email format per FR-003 (partial)" in message


def test_ac07_shows_each_failing_command_with_its_last_30_lines():
    message = compose(_result(), 0, False)
    assert "$ pytest -q" in message
    assert "line 10" in message and "line 39" in message
    assert "line 09" not in message
    assert "ruff check" not in message and "All checks passed!" not in message


def test_ac07_lists_guard_messages_and_ends_with_tail():
    message = compose(_result(), 0, False)
    assert "T015 [US2] is checked, but no passing test cites US2." in message
    assert TAIL == SPEC_TAIL
    assert message.endswith(TAIL)


def test_ac07_guard_only_red_still_ends_with_tail():
    result = _result(outcomes=[_outcome(code=0, output="ok")], failing=[], ids=[], tasks_for_ids=[])
    message = compose(result, 0, False)
    assert "T015 [US2] is checked" in message
    assert "$ pytest -q" not in message
    assert message.endswith(TAIL)
