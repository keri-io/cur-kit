"""Converge keeps going when Spec Kit appended work, including when the reply hook was skipped."""

from __future__ import annotations

import json

from curkit.hooks import on_stop
from curkit.skill_loop import note_prompt, note_response
from tests.test_check import GREEN, add_speckit, make_project, write

CONVERGE = {"followup_message": "/speckit-converge"}
IMPLEMENT = {"followup_message": "/speckit-implement"}
DONE = "Converged — the implementation satisfies the spec, plan, and tasks. No further implement pass is needed."
SKILL = 'name: "speckit-converge"\n\n## Goal\n\n`/speckit-implement` can complete it.\n'
NEW = "\n- [ ] T099 Close the gap per FR-003 (missing)\n"
OPEN = """\
## Phase 3: User Story 1
- [ ] T014 [US1] Implement login redirect in src/auth.py
- [ ] T042 Add export per US1/AC2 (missing)
"""


def ready(tmp_path, monkeypatch):
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)
    root = make_project(tmp_path)
    write(root, "cases.json", json.dumps(GREEN))
    add_speckit(root, monkeypatch, OPEN)
    payload = {"conversation_id": "chat", "status": "completed", "loop_count": 0, "workspace_roots": [str(root)]}
    return root, payload


def test_a_negated_converged_word_still_asks_for_implement(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    text = "The work has not converged. Run /speckit-implement to finish the appended tasks."
    note_prompt(root, {**payload, "prompt": "/speckit-converge"})
    note_response(root, {**payload, "text": text})
    assert on_stop(payload) == IMPLEMENT


def test_a_skipped_reply_asks_for_implement_when_converge_appended_a_task(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-implement"})
    note_response(root, {**payload, "text": "implemented"})
    assert on_stop(payload) == CONVERGE
    path = root / "specs/001-x/tasks.md"
    path.write_text(path.read_text(encoding="utf-8") + NEW, encoding="utf-8")
    assert on_stop(payload) == IMPLEMENT


def test_a_skipped_reply_stops_when_converge_leaves_existing_open_tasks_unchanged(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-converge"})
    assert on_stop(payload) == {}


def test_appended_work_wins_over_a_converged_sentence(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-converge"})
    path = root / "specs/001-x/tasks.md"
    path.write_text(path.read_text(encoding="utf-8") + NEW, encoding="utf-8")
    note_response(root, {**payload, "text": f"{DONE} Do not run /speckit-implement."})
    assert on_stop(payload) == IMPLEMENT


def test_checking_off_an_old_task_does_not_hide_a_new_one(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-converge"})
    path = root / "specs/001-x/tasks.md"
    path.write_text(path.read_text(encoding="utf-8").replace("- [ ] T014", "- [x] T014", 1) + NEW, encoding="utf-8")
    assert on_stop(payload) == IMPLEMENT


def test_checking_off_a_task_without_appending_one_stops(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-converge"})
    path = root / "specs/001-x/tasks.md"
    path.write_text(path.read_text(encoding="utf-8").replace("- [ ] T014", "- [x] T014", 1), encoding="utf-8")
    assert on_stop(payload) == {}


def test_a_paraphrase_without_the_command_continues_when_a_task_was_appended(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-converge"})
    path = root / "specs/001-x/tasks.md"
    path.write_text(path.read_text(encoding="utf-8") + NEW, encoding="utf-8")
    text = "I added the remaining work under Phase 8: Convergence. Please implement those tasks."
    note_response(root, {**payload, "text": text})
    assert on_stop(payload) == IMPLEMENT


def test_the_stock_skill_text_stays_a_converge_turn(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-converge\n\n" + SKILL})
    note_response(root, {**payload, "text": "Recommend running /speckit-implement to complete them."})
    assert on_stop(payload) == IMPLEMENT


def test_the_chain_runs_until_the_tasks_file_stays_still(tmp_path, monkeypatch):
    root, payload = ready(tmp_path, monkeypatch)
    note_prompt(root, {**payload, "prompt": "/speckit-implement"})
    note_response(root, {**payload, "text": "done"})
    assert on_stop(payload) == CONVERGE
    path = root / "specs/001-x/tasks.md"
    path.write_text(path.read_text(encoding="utf-8") + NEW, encoding="utf-8")
    assert on_stop(payload) == IMPLEMENT
    assert on_stop(payload) == CONVERGE
    note_response(root, {**payload, "text": DONE})
    assert on_stop(payload) == {}
