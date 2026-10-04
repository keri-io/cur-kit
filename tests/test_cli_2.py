"""AC-19 and AC-20 through the CLI: `cur-kit hook <event>` always prints JSON and exits 0. R5 and R9 for the CLI."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from curkit import check, hooks
from curkit.__main__ import main
from curkit.state import State
from tests.test_check import FAILING, make_project
from tests.test_cli import BIN, cli

SHOW_ENV = "echo PYTHONPATH=${PYTHONPATH-unset} CUR_KIT_ROOT=${CUR_KIT_ROOT-unset}"

BAD_INPUT = [
    (["hook", "stop"], "not json"),
    (["hook", "stop"], "[1, 2]"),
    (["hook", "stop"], ""),
    (["hook", "session-start"], '"a string"'),
    (["hook", "bogus"], "{}"),
    (["hook"], "{}"),
]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def hook(cwd: Path, event: str, stdin: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([str(BIN), "hook", event], cwd=cwd, input=stdin, capture_output=True, timeout=120, check=False)


def explode(*args: object) -> dict:
    raise RuntimeError("boom")


def test_ac19_hook_stop_prints_a_followup_through_bin_cur_kit(tmp_path):
    root = make_project(tmp_path)
    payload = {"status": "completed", "loop_count": 0, "workspace_roots": [str(root)]}
    done = hook(tmp_path, "stop", json.dumps(payload).encode())
    assert done.returncode == 0, done.stderr
    message = json.loads(done.stdout)["followup_message"]
    assert FAILING in message and "US1/AC2" in message and "(1/25)" in message


@pytest.mark.parametrize("case", BAD_INPUT)
def test_ac19_hook_prints_empty_json_and_exits_0_on_bad_input(monkeypatch, capsys, case):
    args, stdin = case
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_ac19_hook_survives_undecodable_stdin_and_a_raising_handler(tmp_path, monkeypatch, capsys):
    done = hook(tmp_path, "stop", b"\xff\xfe{")
    assert (done.returncode, json.loads(done.stdout)) == (0, {})
    monkeypatch.setattr(hooks, "on_stop", explode)
    monkeypatch.setattr("sys.stdin", io.StringIO('{"status": "completed"}'))
    assert main(["hook", "stop"]) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_ac20_hook_session_start_clears_the_latch(tmp_path):
    root = make_project(tmp_path)
    State(root).save_latch({"failure": "abc", "count": 2})
    done = hook(tmp_path, "session-start", json.dumps({"workspace_roots": [str(root)]}).encode())
    assert (done.returncode, json.loads(done.stdout)) == (0, {})
    assert State(root).latch() == {"failure": None, "count": 0}


def test_ac21_no_arguments_prints_the_usage(capsys):
    assert main([]) == 2
    assert "usage: cur-kit" in capsys.readouterr().out


def test_r5_project_commands_run_with_the_users_pythonpath_unchanged(tmp_path, monkeypatch):
    root = make_project(tmp_path, {"test": SHOW_ENV, "junit": "", "cache": False})
    monkeypatch.setenv("PYTHONPATH", "/user/lib")
    seen = [json.loads(cli(root, "check", "--json").stdout)["outcomes"][0]["output"]]
    monkeypatch.delenv("PYTHONPATH")
    seen.append(json.loads(cli(root, "check", "--json").stdout)["outcomes"][0]["output"])
    assert seen == ["PYTHONPATH=/user/lib CUR_KIT_ROOT=unset", "PYTHONPATH=unset CUR_KIT_ROOT=unset"]


def test_r9_check_prints_json_and_exits_0_when_the_check_breaks(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(check, "run_check", explode)
    assert main(["check", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"configured": True, "ok": False, "red": True, "error": "RuntimeError: boom"}
