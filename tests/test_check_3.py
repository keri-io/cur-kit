"""Review round for run_check: output caps (R1), tracked edits mid-run (R2), JUnit-only red (R3), R8, R10, R11."""

from __future__ import annotations

import json

from curkit.check import run_check
from curkit.state import STATE_DIR
from tests.test_check import CONFIG, FAILING, git, make_project, ran, write

ARGUMENT_LIMIT = 128 * 1024
HUGE = """\
import pathlib, sys
if sys.argv[1:] == ["report"]:
    names = [f"tests/test_big.py::test_case_{n:04d}_" + "x" * 80 for n in range(500)]
    rows = "".join(f'<testcase name="{name}"><failure/></testcase>' for name in names)
    pathlib.Path(".cursor/report.xml").write_text(f"<testsuite>{rows}</testsuite>")
for n in range(300):
    print(f"FAILED line {n:03d} " + "y" * 1000)
sys.exit(1)
"""
MIXED_OUTPUT = """\
print("PASSED tests/test_auth.py::test_US1_AC1_shows_form")
print("FAILED tests/test_auth.py::test_US1_AC2_redirects")
print("tests/test_api.py::test_fr_003_validates Error: boom")
print("see US9 in the docs, then rerun")
raise SystemExit(1)
"""
PREREQ = "echo called >> {log}\necho '{{\"FEATURE_DIR\": \"specs/001-x\"}}'\n"


def test_r1_a_huge_output_stays_under_the_argument_limit(tmp_path):
    root = make_project(tmp_path, {"test": "python3 huge.py report", "lint": "python3 huge.py",
                                   "typecheck": "python3 huge.py"})
    write(root, "huge.py", HUGE)
    result = run_check(root)
    outputs = [outcome["output"] for outcome in result["outcomes"]]
    assert len(outputs) == 3 and all(len(text) <= 4000 and len(text.splitlines()) <= 30 for text in outputs)
    assert all("FAILED line 299" in text and "FAILED line 269" not in text for text in outputs)
    assert len(result["failing"]) == 50 and result["failing"][-1].startswith("tests/test_big.py::test_case_0049_")
    assert len(json.dumps(result)) < ARGUMENT_LIMIT


def test_r2_a_tracked_edit_during_the_run_stores_no_key_so_the_next_call_runs_again(tmp_path):
    root = make_project(tmp_path, {"test": f"echo edited >> notes.txt; {CONFIG['test']}"})
    write(root, "notes.txt", "before\n")
    git(root, "add", "notes.txt")
    git(root, "commit", "-q", "--no-verify", "-m", "notes")
    first = run_check(root)
    assert first["key"] is None and json.loads((root / STATE_DIR / "last-run.json").read_text())["key"] is None
    second = run_check(root)
    assert not second["reused"] and ran(root) == 2 and second["failing"] == [FAILING]


def test_r2_a_tracked_junit_report_that_comes_back_the_same_still_allows_reuse(tmp_path):
    root = make_project(tmp_path)
    run_check(root)
    git(root, "add", CONFIG["junit"])
    git(root, "commit", "-q", "--no-verify", "-m", "track the report")
    second = run_check(root)
    third = run_check(root)
    assert second["key"] is not None and third["reused"] and ran(root) == 2


def test_r3_a_command_that_exits_0_with_junit_failures_is_red(tmp_path):
    result = run_check(make_project(tmp_path, {"test": f"{CONFIG['test']} || true"}))
    assert result["ok"] and result["failing"] == [FAILING] and result["red"]


def test_r8_unplanned_leaves_out_the_junit_report(tmp_path):
    root = make_project(tmp_path, {"test": "python3 suite.py report.xml", "junit": "./report.xml"})
    write(root, "src/extra.py", "x = 1\n")
    result = run_check(root)
    assert result["failing"] == [FAILING] and result["unplanned"] == ["src/extra.py"]


def test_r10_without_junit_ids_come_only_from_failure_and_error_lines(tmp_path):
    root = make_project(tmp_path, {"test": "python3 out.py", "junit": ""})
    write(root, "out.py", MIXED_OUTPUT)
    assert run_check(root)["ids"] == ["US1/AC2", "FR-003"]


def test_r11_resolves_the_feature_folder_once_per_call(tmp_path, monkeypatch):
    monkeypatch.delenv("SPECIFY_FEATURE_DIRECTORY", raising=False)
    root = make_project(tmp_path)
    log = tmp_path / "prereq.log"
    write(root, ".specify/scripts/bash/check-prerequisites.sh", PREREQ.format(log=log))
    result = run_check(root)
    assert (result["feature_dir"], result["open"]) == ("specs/001-x", 0)
    assert len(log.read_text().splitlines()) == 1
