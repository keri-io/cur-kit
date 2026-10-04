"""AC-17: run_check runs the commands or reuses the last run. The temp-project helpers for check, hooks, and CLI tests."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from curkit.check import run_check
from curkit.config import CONFIG_PATH
from curkit.state import STATE_DIR

FAILING = "tests/test_auth.py::test_US1_AC2_redirects"
PASSING = "tests/test_auth.py::test_US1_AC1_shows_form"
RED, GREEN = {PASSING: "pass", FAILING: "fail"}, {PASSING: "pass", FAILING: "pass"}
CONFIG = {"test": "python3 suite.py .cursor/report.xml", "junit": ".cursor/report.xml"}
GIT_CONFIG = (("user.email", "opus-c@example.com"), ("user.name", "Opus C"), ("commit.gpgsign", "false"))
TASKS = """\
## Phase 3: User Story 1
- [ ] T014 [US1] Implement login redirect in src/auth.py
- [x] T015 [US2] Add logout in src/logout.py
- [ ] T042 Add export per US1/AC2 (missing)
"""
SUITE = """\
import json, pathlib, sys
cases = json.loads(pathlib.Path("cases.json").read_text())
with open("ran.log", "a") as log:
    log.write("ran\\n")
body = {"fail": "<failure message='boom'/>", "skip": "<skipped/>"}
rows = "".join(f'<testcase name="{name}">{body.get(status, "")}</testcase>' for name, status in cases.items())
if len(sys.argv) > 1:
    pathlib.Path(sys.argv[1]).write_text(f"<testsuites><testsuite>{rows}</testsuite></testsuites>")
print("\\n".join(f"FAILED {name}" if status == "fail" else "." for name, status in cases.items()))
sys.exit(1 if "fail" in cases.values() else 0)
"""
IDLE = {
    "configured": False, "ok": True, "red": False, "reused": False, "key": None, "outcomes": [], "failing": [],
    "ids": [], "tasks_for_ids": [], "open": 0, "open_tasks": [], "guard": None, "unplanned": [], "feature_dir": None,
}


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_project(tmp_path: Path, settings: dict | None = None) -> Path:
    """A committed git project whose fake suite writes JUnit for cases.json and exits 1 while a case fails."""
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q")
    for key, value in GIT_CONFIG:
        git(root, "config", key, value)
    write(root, ".gitignore", "ran.log\n")
    write(root, "suite.py", SUITE)
    write(root, "cases.json", json.dumps(RED))
    write(root, CONFIG_PATH, json.dumps({**CONFIG, **(settings or {})}))
    git(root, "add", ".")
    git(root, "commit", "-q", "--no-verify", "-m", "init")
    return root


def ran(root: Path) -> int:
    """How many times the fake suite ran. ran.log is gitignored, so counting never changes the tree."""
    log = root / "ran.log"
    return len(log.read_text().splitlines()) if log.exists() else 0


def add_speckit(root: Path, monkeypatch: pytest.MonkeyPatch, tasks: str = TASKS) -> Path:
    (root / ".specify").mkdir()
    monkeypatch.setenv("SPECIFY_FEATURE_DIRECTORY", "specs/001-x")
    return write(root, "specs/001-x/tasks.md", tasks)


def test_ac17_is_not_configured_without_a_config_or_test_command(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    (root / CONFIG_PATH).unlink()
    assert run_check(root) == IDLE
    write(root, CONFIG_PATH, json.dumps({"test": "  ", "lint": "python3 suite.py"}))
    add_speckit(root, monkeypatch)
    assert run_check(root) == {**IDLE, "open": 2, "open_tasks": ["T014", "T042"], "feature_dir": "specs/001-x"}
    assert ran(root) == 0 and not (root / STATE_DIR).exists()


def test_ac17_fills_every_field_of_the_check_result_from_a_fresh_run(tmp_path):
    result = run_check(make_project(tmp_path))
    assert set(result) == set(IDLE)
    assert result["configured"] and not result["ok"] and result["red"] and not result["reused"]
    assert re.fullmatch(r"[0-9a-f]{64}", result["key"])
    assert result["failing"] == [FAILING] and result["ids"] == ["US1/AC2"]
    [outcome] = result["outcomes"]
    assert set(outcome) == {"name", "command", "code", "timed_out", "seconds", "output"}
    assert (outcome["name"], outcome["command"], outcome["code"], outcome["timed_out"]) == ("test", CONFIG["test"], 1, False)
    assert f"FAILED {FAILING}" in outcome["output"] and outcome["seconds"] >= 0
    assert result["guard"] == [] and result["tasks_for_ids"] == [] and result["unplanned"] == []
    assert (result["open"], result["open_tasks"], result["feature_dir"]) == (0, [], None)


def test_ac17_reuses_the_last_run_when_nothing_changed(tmp_path):
    root = make_project(tmp_path)
    first = run_check(root)
    second = run_check(root)
    assert ran(root) == 1 and not first["reused"] and second["reused"]
    assert {**second, "reused": False} == first


def test_ac17_runs_again_when_the_tree_changes(tmp_path):
    root = make_project(tmp_path)
    first = run_check(root)
    write(root, "cases.json", json.dumps(GREEN))
    second = run_check(root)
    assert ran(root) == 2 and not second["reused"] and second["key"] != first["key"]
    assert second["ok"] and not second["red"] and second["failing"] == [] and second["ids"] == []
    assert run_check(root)["reused"] and ran(root) == 2


def test_ac17_runs_every_time_when_cache_is_off(tmp_path):
    root = make_project(tmp_path, {"cache": False})
    results = [run_check(root) for _ in range(3)]
    assert ran(root) == 3 and [result["reused"] for result in results] == [False] * 3
    assert len({result["key"] for result in results}) == 1
