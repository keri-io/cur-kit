"""AC-08: skipped cases are neither failed nor passing, so they never satisfy the guard."""

from __future__ import annotations

from pathlib import Path

from curkit.guard import violations
from curkit.junit import Case, read_junit
from curkit.tasks import parse_tasks
from tests.test_guard import _task

SKIPPED = Case(name="tests.test_auth::test_US1_AC2_redirects", failed=False, skipped=True)
PASSING = Case(name="tests.test_auth::test_US1_AC1_renders", failed=False)
FAILING = Case(name="tests.test_auth::test_US1_AC3_logs_out", failed=True)


def test_ac08_only_citing_case_skipped_is_flagged_and_says_skipped():
    assert violations([_task("T014", "US1")], [SKIPPED]) == [
        "T014 [US1] is checked, but the only test citing US1 was skipped: tests.test_auth::test_US1_AC2_redirects."
    ]


def test_ac08_several_skipped_citing_cases_are_all_named():
    other = Case(name="tests.test_auth::test_us1_login", failed=False, skipped=True)
    names = f"{SKIPPED.name}, {other.name}"
    assert violations([_task("T014", "US1")], [SKIPPED, other]) == [
        f"T014 [US1] is checked, but every test citing US1 was skipped: {names}."
    ]


def test_ac08_a_skipped_case_beside_a_passing_case_is_fine():
    assert violations([_task("T014", "US1")], [SKIPPED, PASSING]) == []


def test_ac08_a_failing_case_outranks_a_skipped_one():
    assert violations([_task("T014", "US1")], [SKIPPED, FAILING]) == [
        "T014 [US1] is checked, but a failing test cites US1: tests.test_auth::test_US1_AC3_logs_out."
    ]


def test_ac08_skipped_case_in_a_junit_report_does_not_check_off_the_task(tmp_path: Path):
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuites><testsuite><testcase classname="tests.test_export" name="test_US2_AC1_exports">'
        '<skipped message="later"/></testcase><testcase classname="tests.test_login" name="test_US1_AC1_form"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    tasks = parse_tasks("- [x] T013 [US1] Add login form in src/ui/login.py\n- [x] T020 [US2] Export in src/export.py\n")
    assert violations(tasks, read_junit(report)) == [
        "T020 [US2] is checked, but the only test citing US2 was skipped: tests.test_export::test_US2_AC1_exports."
    ]
