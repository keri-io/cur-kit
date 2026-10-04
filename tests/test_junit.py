"""AC-03: read_junit for pytest, Jest, and Bun reports."""

from __future__ import annotations

from pathlib import Path

from curkit.junit import Case, read_junit

PYTEST = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="1" tests="3" time="0.05">
    <testcase classname="tests.test_auth" name="test_US1_AC2_redirects" time="0.010">
      <failure message="assert False">Traceback (most recent call last)</failure>
    </testcase>
    <testcase classname="tests.test_auth" name="test_US1_AC1_renders" time="0.010" />
    <testcase classname="tests.test_auth" name="test_US2_AC1_exports" time="0.000">
      <skipped type="pytest.skip" message="not yet" />
    </testcase>
  </testsuite>
</testsuites>
"""

JEST = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="jest tests" tests="2" failures="1" errors="0" time="0.5">
  <testsuite name="login" errors="0" failures="1" skipped="0" timestamp="2026-10-04T00:00:00" time="0.1" tests="2">
    <testcase classname="login US1 AC2 redirects after login" name="login US1 AC2 redirects after login" time="0.004">
      <failure>Error: expect(received).toBe(expected)</failure>
    </testcase>
    <testcase classname="login FR-003 validates email" name="login FR-003 validates email" time="0.001" />
  </testsuite>
</testsuites>
"""

BUN = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="bun test" tests="3" assertions="3" failures="0" errors="1" skipped="1" time="0.02">
  <testsuite name="src/auth.test.ts" file="src/auth.test.ts" tests="3">
    <testsuite name="US1" tests="2">
      <testcase name="AC2 redirects" classname="US1" file="src/auth.test.ts" line="4">
        <error type="TypeError" message="boom">stack</error>
      </testcase>
      <testcase name="AC1 renders" classname="US1" file="src/auth.test.ts" line="9" />
    </testsuite>
    <testcase name="sc_002 responds fast" file="src/auth.test.ts" line="14">
      <skipped />
    </testcase>
  </testsuite>
</testsuites>
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(text, encoding="utf-8")
    return path


def test_ac03_reads_pytest_report_failure_pass_and_skip(tmp_path: Path):
    assert read_junit(_write(tmp_path, PYTEST)) == [
        Case(name="tests.test_auth::test_US1_AC2_redirects", failed=True),
        Case(name="tests.test_auth::test_US1_AC1_renders", failed=False),
        Case(name="tests.test_auth::test_US2_AC1_exports", failed=False, skipped=True),
    ]


def test_ac03_skipped_case_is_marked_skipped_and_not_failed(tmp_path: Path):
    text = '<testsuite><testcase classname="t" name="test_US2_AC1_exports"><skipped message="later"/></testcase></testsuite>'
    (case,) = read_junit(_write(tmp_path, text))
    assert (case.failed, case.skipped) == (False, True)
    passing, failing = read_junit(_write(tmp_path, PYTEST))[1], read_junit(_write(tmp_path, PYTEST))[0]
    assert (passing.failed, passing.skipped) == (False, False)
    assert (failing.failed, failing.skipped) == (True, False)


def test_ac03_case_defaults_skipped_to_false_for_stored_runs():
    assert Case("x", False) == Case(name="x", failed=False, skipped=False)
    old_record, new_record = {"name": "x", "failed": True}, {"name": "x", "failed": False, "skipped": True}
    assert Case(**old_record).skipped is False
    assert Case(**new_record).skipped is True


def test_ac03_reads_jest_report(tmp_path: Path):
    cases = read_junit(_write(tmp_path, JEST))
    assert cases == [
        Case(name="login US1 AC2 redirects after login::login US1 AC2 redirects after login", failed=True),
        Case(name="login FR-003 validates email::login FR-003 validates email", failed=False),
    ]


def test_ac03_reads_bun_nested_suites_error_is_failed_and_skipped_is_not(tmp_path: Path):
    assert read_junit(_write(tmp_path, BUN)) == [
        Case(name="US1::AC2 redirects", failed=True),
        Case(name="US1::AC1 renders", failed=False),
        Case(name="sc_002 responds fast", failed=False, skipped=True),
    ]


def test_ac03_single_testsuite_root_and_empty_classname(tmp_path: Path):
    text = '<testsuite tests="1"><testcase classname="" name="test_fr_003"/></testsuite>'
    assert read_junit(_write(tmp_path, text)) == [Case(name="test_fr_003", failed=False)]


def test_ac03_report_without_cases_is_an_empty_list(tmp_path: Path):
    assert read_junit(_write(tmp_path, "<testsuites></testsuites>")) == []


def test_ac03_missing_file_returns_none(tmp_path: Path):
    assert read_junit(tmp_path / "absent.xml") is None
    assert read_junit(tmp_path) is None


def test_ac03_malformed_file_returns_none(tmp_path: Path):
    assert read_junit(_write(tmp_path, "<testsuites><testcase name='x'>")) is None
    assert read_junit(_write(tmp_path, "")) is None
    assert read_junit(_write(tmp_path, "not xml at all")) is None
