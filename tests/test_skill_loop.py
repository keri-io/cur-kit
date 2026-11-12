"""After implement, stop asks for converge. After converge, stop asks for implement only when asked."""

from __future__ import annotations

import io
import json

import pytest

from curkit.__main__ import main
from curkit.hooks import on_stop
from curkit.skill_loop import note_prompt, note_response
from tests.test_check import FAILING, GREEN, make_project, write

CONVERGE = {"followup_message": "/speckit-converge"}
IMPLEMENT = {"followup_message": "/speckit-implement"}


@pytest.fixture(autouse=True)
def no_cursor_env(monkeypatch):
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def turn(root, prompt, response=""):
    base = {"conversation_id": "chat", "status": "completed", "loop_count": 0, "workspace_roots": [str(root)]}
    note_prompt(root, {**base, "prompt": prompt})
    note_response(root, {**base, "text": response})
    return on_stop(base)


@pytest.mark.parametrize("prompt", ["/speckit-implement", "run /speckit.implement"])
def test_green_implement_submits_converge(tmp_path, prompt):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    assert turn(root, prompt) == CONVERGE


def test_red_implement_keeps_the_suite_followup_until_a_later_green_stop(tmp_path):
    root = make_project(tmp_path)
    red = turn(root, "/speckit-implement")
    assert FAILING in red["followup_message"] and "/speckit-converge" not in red["followup_message"]
    write(root, "cases.json", json.dumps(GREEN))
    assert turn(root, "fix the red suite") == CONVERGE


@pytest.mark.parametrize("text", ["Run /speckit-implement next.", "Run /speckit.implement next."])
def test_converge_that_names_implement_submits_it(tmp_path, text):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    assert turn(root, "/speckit-converge", text) == IMPLEMENT


def test_converged_reply_submits_nothing(tmp_path):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    text = "Converged — the implementation satisfies the spec, plan, and tasks. No further implement pass is needed."
    assert turn(root, "/speckit-converge", text) == {}


def test_converge_without_naming_implement_submits_nothing(tmp_path):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    assert turn(root, "/speckit.converge", "Checked 12 requirements. Nothing remains.") == {}


def test_converged_reply_that_also_names_implement_submits_nothing(tmp_path):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    assert turn(root, "/speckit-converge", "Converged. Do not run /speckit-implement.") == {}


def test_loop_limit_submits_nothing(tmp_path):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    base = {"conversation_id": "chat", "status": "completed", "loop_count": 25, "workspace_roots": [str(root)]}
    note_prompt(root, {**base, "prompt": "/speckit-implement"})
    assert on_stop(base) == {}


def test_cli_records_the_prompt_and_the_reply_for_the_stop_hook(tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    monkeypatch.chdir(root)
    roots = {"workspace_roots": [str(root)]}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({**roots, "prompt": "/speckit-implement"})))
    assert main(["hook", "before-submit"]) == 0
    assert json.loads(capsys.readouterr().out) == {"continue": True}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({**roots, "text": "implemented"})))
    assert main(["hook", "after-response"]) == 0
    capsys.readouterr()
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({**roots, "status": "completed"})))
    assert main(["hook", "stop"]) == 0
    assert json.loads(capsys.readouterr().out) == CONVERGE
