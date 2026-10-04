"""AC-17: the key's salt, stale JUnit, ids without JUnit, the run log, no git, unreadable state, and tasks.md fields."""

from __future__ import annotations

import json
import shutil
from datetime import datetime

from curkit.check import run_check
from curkit.config import CONFIG_PATH
from curkit.state import STATE_DIR
from tests.test_check import CONFIG, FAILING, GREEN, TASKS, add_speckit, git, make_project, ran, write

LOG_KEYS = {"at", "key", "reused", "ok", "red", "seconds", "ids", "open"}
US2_GUARD = "T015 [US2] is checked, but no passing test cites US2."


def test_ac17_salts_the_key_with_the_commands_and_the_junit_path(tmp_path):
    root = make_project(tmp_path)
    git(root, "rm", "-q", "--cached", CONFIG_PATH)
    write(root, ".gitignore", f"ran.log\n{CONFIG_PATH}\n")
    git(root, "commit", "-q", "-a", "--no-verify", "-m", "ignore the config so only the salt can change")
    first = run_check(root)
    write(root, CONFIG_PATH, json.dumps({**CONFIG, "timeout": 120, "cache": True}))
    assert run_check(root)["reused"], "timeout and cache are not part of the key"
    write(root, CONFIG_PATH, json.dumps({**CONFIG, "lint": "echo lint"}))
    second = run_check(root)
    write(root, CONFIG_PATH, json.dumps({**CONFIG, "lint": "echo lint", "junit": ".cursor/other.xml"}))
    third = run_check(root)
    assert not second["reused"] and not third["reused"] and ran(root) == 3
    assert len({first["key"], second["key"], third["key"]}) == 3


def test_ac17_deletes_a_stale_junit_file_before_running(tmp_path):
    root = make_project(tmp_path, {"test": "python3 suite.py"})
    report = write(root, ".cursor/report.xml", f'<testsuite><testcase name="{FAILING}"><failure/></testcase></testsuite>')
    write(root, "cases.json", json.dumps(GREEN))
    result = run_check(root)
    assert not report.exists()
    assert result["ok"] and not result["red"] and result["failing"] == [] and result["guard"] is None


def test_ac17_takes_ids_from_the_failing_output_without_junit(tmp_path):
    result = run_check(make_project(tmp_path, {"junit": "", "lint": "echo lint cites US3/AC1"}))
    assert result["red"] and result["failing"] == [] and result["guard"] is None
    assert result["ids"] == ["US1/AC2"]


def test_ac17_logs_each_run(tmp_path):
    root = make_project(tmp_path)
    results = [run_check(root), run_check(root)]
    entries = [json.loads(line) for line in (root / STATE_DIR / "runs.jsonl").read_text().splitlines()]
    assert [set(entry) for entry in entries] == [LOG_KEYS, LOG_KEYS]
    picked = [(e["key"], e["reused"], e["ok"], e["red"], e["ids"], e["open"]) for e in entries]
    assert picked == [(r["key"], r["reused"], False, True, ["US1/AC2"], 0) for r in results]
    assert [result["reused"] for result in results] == [False, True]
    assert all(datetime.fromisoformat(e["at"]).tzinfo and e["seconds"] >= 0 for e in entries)


def test_ac17_runs_without_a_key_outside_git(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    root = make_project(tmp_path)
    shutil.rmtree(root / ".git")
    first, second = run_check(root), run_check(root)
    assert first["key"] is None and second["key"] is None and not second["reused"]
    assert ran(root) == 2 and second["failing"] == [FAILING] and second["unplanned"] == []


def test_ac17_runs_again_when_the_stored_run_cannot_be_read(tmp_path):
    root = make_project(tmp_path)
    run_check(root)
    stored = root / STATE_DIR / "last-run.json"
    record = json.loads(stored.read_text())
    stored.write_text(json.dumps({**record, "cases": [{"name": FAILING, "failed": True, "flaky": True}]}))
    assert not run_check(root)["reused"]
    stored.write_text(json.dumps({key: value for key, value in record.items() if key != "ids"}))
    assert not run_check(root)["reused"]
    assert run_check(root)["reused"] and ran(root) == 3


def test_ac17_fills_the_plan_fields_from_tasks_md(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    add_speckit(root, monkeypatch, TASKS + "- [ ] T050 Wire the views in src/views/\n")
    for name in ("src/auth.py", "src/views/home.py", "src/extra.py", "specs/notes.md", ".cursor/scratch.md"):
        write(root, name, "x = 1\n")
    result = run_check(root)
    assert result["feature_dir"] == "specs/001-x"
    assert (result["open"], result["open_tasks"]) == (3, ["T014", "T042", "T050"])
    assert result["tasks_for_ids"] == [{"id": "T042", "text": "T042 Add export per US1/AC2 (missing)"}]
    assert result["unplanned"] == ["src/extra.py"]


def test_ac17_guard_turns_a_passing_run_red(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    add_speckit(root, monkeypatch)
    result = run_check(root)
    assert result["ok"] and result["red"] and result["guard"] == [US2_GUARD]


def test_ac17_keeps_skipped_cases_through_a_reused_run(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps({**GREEN, "tests/test_logout.py::test_US2_AC1_logs_out": "skip"}))
    add_speckit(root, monkeypatch)
    first, second = run_check(root), run_check(root)
    assert first["ok"] and first["red"] and len(first["guard"]) == 1 and "skipped" in first["guard"][0]
    assert second["reused"] and second["guard"] == first["guard"]


def test_ac17_recomputes_tasks_and_guard_on_a_reused_run(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    add_speckit(root, monkeypatch)
    write(root, "specs/002-y/tasks.md", "- [ ] T001 [US3] Add search\n- [x] T002 [US1] Implement login in src/auth.py\n")
    first = run_check(root)
    monkeypatch.setenv("SPECIFY_FEATURE_DIRECTORY", "specs/002-y")
    second = run_check(root)
    assert second["reused"] and ran(root) == 1 and second["feature_dir"] == "specs/002-y"
    assert (first["open_tasks"], second["open_tasks"]) == (["T014", "T042"], ["T001"])
    assert second["tasks_for_ids"] == [{"id": "T002", "text": "T002 [US1] Implement login in src/auth.py"}]
    assert first["guard"] == [US2_GUARD]
    assert len(second["guard"]) == 1 and second["guard"][0].startswith("T002 [US1] is checked")
