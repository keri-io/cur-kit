"""Cloud stops keep the skill loop when the prompt hook is skipped or the skill text names both commands."""

from __future__ import annotations

import json

import pytest

from curkit.hooks import on_stop
from curkit.skill_loop import note_prompt, note_response
from tests.test_check import GREEN, make_project, write

CONVERGE = {"followup_message": "/speckit-converge"}
IMPLEMENT = {"followup_message": "/speckit-implement"}
BOTH = "/speckit-converge\n\nThe skill later says to run /speckit-implement for remaining tasks."


@pytest.fixture(autouse=True)
def no_cursor_env(monkeypatch):
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def green(tmp_path):
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    return root


def test_a_converge_prompt_that_mentions_implement_stays_a_converge_turn(tmp_path):
    root = green(tmp_path)
    base = {"status": "completed", "loop_count": 0, "conversation_id": "chat", "workspace_roots": [str(root)]}
    note_prompt(root, {**base, "prompt": BOTH})
    note_response(root, {**base, "text": "Run /speckit-implement to complete them."})
    assert on_stop(base) == IMPLEMENT


def test_stop_adopts_a_chat_id_the_prompt_hook_did_not_have(tmp_path):
    root = green(tmp_path)
    roots = {"workspace_roots": [str(root)]}
    note_prompt(root, {**roots, "prompt": "/speckit-converge"})
    note_response(root, {**roots, "text": "Run /speckit-implement next."})
    stop = {"status": "completed", "loop_count": 0, "conversation_id": "cloud-chat", **roots}
    assert on_stop(stop) == IMPLEMENT


def test_a_skipped_prompt_hook_sees_the_command_the_previous_stop_submitted(tmp_path):
    root = green(tmp_path)
    base = {"status": "completed", "loop_count": 0, "conversation_id": "chat", "workspace_roots": [str(root)]}
    note_prompt(root, {**base, "prompt": "/speckit-implement"})
    note_response(root, {**base, "text": "implemented the tasks"})
    assert on_stop(base) == CONVERGE
    note_response(root, {**base, "text": "Run /speckit-implement to complete them."})
    again = {**base, "loop_count": 1}
    assert on_stop(again) == IMPLEMENT


def test_a_different_conversation_does_not_keep_the_previous_skill(tmp_path):
    root = green(tmp_path)
    base = {"status": "completed", "loop_count": 0, "conversation_id": "chat", "workspace_roots": [str(root)]}
    note_prompt(root, {**base, "prompt": "/speckit-implement"})
    assert on_stop(base) == CONVERGE
    other = {**base, "conversation_id": "other-chat"}
    assert on_stop(other) == {}
