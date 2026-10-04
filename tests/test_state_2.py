"""AC-06: a failure is reported twice at most, and its print ignores order and timings."""

from __future__ import annotations

import re

from curkit.state import failure_print, should_report

EMPTY = {"failure": None, "count": 0}


def test_ac06_new_failure_is_reported_with_count_one() -> None:
    assert should_report(EMPTY, "abc") == (True, {"failure": "abc", "count": 1})
    assert should_report({"failure": "old", "count": 2}, "abc") == (True, {"failure": "abc", "count": 1})


def test_ac06_same_failure_is_reported_once_more_with_count_two() -> None:
    assert should_report({"failure": "abc", "count": 1}, "abc") == (True, {"failure": "abc", "count": 2})


def test_ac06_after_two_reports_it_stays_quiet_until_the_failure_changes() -> None:
    latch, reports, counts = dict(EMPTY), [], []
    for failure in ["abc"] * 5 + ["xyz"]:
        report, latch = should_report(latch, failure)
        reports.append(report)
        counts.append(latch["count"])
    assert reports == [True, True, False, False, False, True]
    assert counts[:2] == [1, 2] and all(count >= 2 for count in counts[2:5]) and counts[5] == 1


def test_ac06_should_report_leaves_the_given_latch_alone() -> None:
    latch = {"failure": "abc", "count": 1}
    should_report(latch, "abc")
    assert latch == {"failure": "abc", "count": 1}


def test_ac06_failure_print_uses_sorted_names_when_there_are_any() -> None:
    first = failure_print(["b::test_two", "a::test_one"], "output 1")
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert first == failure_print(["a::test_one", "b::test_two", "a::test_one"], "other output")
    assert first != failure_print(["a::test_one"], "output 1")
    assert failure_print(["x"], "") != failure_print([], "x")


def test_ac06_failure_print_ignores_digits_in_the_output() -> None:
    slow = "FAILED test_login\n1 failed in 12.34s"
    fast = "FAILED test_login\n1 failed in 0.56s"
    assert failure_print([], slow) == failure_print([], fast)
    assert failure_print([], slow) != failure_print([], "FAILED test_logout\n1 failed in 12.34s")


def test_ac06_failure_print_uses_only_the_last_20_output_lines() -> None:
    tail = [f"line {chr(ord('a') + n)}" for n in range(20)]
    assert failure_print([], "\n".join(["early a", *tail])) == failure_print([], "\n".join(["early b", *tail]))
    assert failure_print([], "\n".join(tail)) != failure_print([], "\n".join([*tail[:-1], "changed"]))
