"""A new conversation_id reports a spent failure again. A user stop stays quiet beside a project hook."""

from __future__ import annotations

import io
import json

import pytest

from curkit.__main__ import main
from curkit.hooks import on_stop
from curkit.project_hooks import install_project_hooks
from curkit.state import State
from tests.test_check import make_project, ran


@pytest.fixture(autouse=True)
def no_cursor_env(monkeypatch):
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def _payload(root, chat: str) -> dict:
    return {"status": "completed", "workspace_roots": [str(root)], "conversation_id": chat}


def test_a_new_conversation_id_reports_a_spent_failure_again(tmp_path):
    root = make_project(tmp_path)
    payload = _payload(root, "chat-a")
    assert [bool(on_stop(payload)) for _ in range(3)] == [True, True, False]
    payload["conversation_id"] = "chat-b"
    message = on_stop(payload)["followup_message"]
    latch = State(root).latch()
    assert "(1/25)" in message and latch["count"] == 1 and latch["conversation"] == "chat-b"


def test_an_empty_conversation_id_leaves_the_latch(tmp_path):
    root = make_project(tmp_path)
    payload = _payload(root, "chat-a")
    assert [bool(on_stop(payload)) for _ in range(3)] == [True, True, False]
    payload["conversation_id"] = ""
    assert on_stop(payload) == {}
    latch = State(root).latch()
    assert latch["count"] == 4 and latch["conversation"] == "chat-a"


@pytest.mark.parametrize("command", ["bash .cursor/hooks/cur-kit stop", "/opt/cur-kit/bin/cur-kit hook stop --user"])
def test_user_stop_is_quiet_when_the_project_has_a_cur_kit_stop(tmp_path, command):
    root = make_project(tmp_path)
    path = root / ".cursor" / "hooks.json"
    path.write_text(json.dumps({"hooks": {"stop": [{"command": command}]}}), encoding="utf-8")
    payload = {"status": "completed", "workspace_roots": [str(root)]}
    assert on_stop(payload, user=True) == {}
    assert ran(root) == 0


def test_user_stop_runs_when_the_project_has_no_cur_kit_hook(tmp_path):
    root = make_project(tmp_path)
    payload = {"status": "completed", "workspace_roots": [str(root)]}
    assert "followup_message" in on_stop(payload, user=True)
    assert ran(root) == 1


def test_cli_user_stop_is_quiet_when_the_project_hook_exists(tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path)
    install_project_hooks(root)
    monkeypatch.chdir(root)
    stdin = json.dumps({"status": "completed", "workspace_roots": [str(root)]})
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    assert main(["hook", "stop", "--user"]) == 0
    assert json.loads(capsys.readouterr().out) == {}
    assert ran(root) == 0
