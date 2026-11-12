"""Linear sync uses a fake transport: statuses, duplicates, cycles, and a missing key."""

from __future__ import annotations

import json

import pytest

from curkit.hooks import on_stop
from curkit.linear_sync import sync
from tests.test_check import make_project, write

STATES = [
    {"id": "backlog", "name": "Backlog", "type": "backlog"},
    {"id": "todo", "name": "Todo", "type": "unstarted"},
    {"id": "doing", "name": "In Progress", "type": "started"},
    {"id": "review", "name": "In Review", "type": "started"},
    {"id": "done", "name": "Done", "type": "completed"},
    {"id": "canceled", "name": "Canceled", "type": "canceled"},
]
REPLIES = {
    "mutation LabelCreate": {"data": {"issueLabelCreate": {"issueLabel": {"id": "label"}}}},
    "mutation IssueCreate": {"data": {"issueCreate": {"issue": {"id": "created"}}}},
    "mutation IssueUpdate": {"data": {"issueUpdate": {"success": True}}},
    "mutation Duplicate": {"data": {"issueRelationCreate": {"success": True}}},
    "query Docs": {"data": {"project": {"documents": {"nodes": []}}}},
    "mutation DocCreate": {"data": {"documentCreate": {"document": {"id": "doc", "url": "https://linear.app/doc"}}}},
    "mutation DocUpdate": {"data": {"documentUpdate": {"document": {"url": "https://linear.app/doc"}}}},
    "mutation ProjectStatus": {"data": {"projectUpdate": {"success": True}}},
    "mutation Health": {"data": {"projectUpdateCreate": {"success": True}}},
    "query Labels": {"data": {"team": {"labels": {"nodes": []}}}},
}


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def board(query, variables):
    board.calls.append((query, variables))
    for prefix, body in REPLIES.items():
        if query.startswith(prefix):
            return body
    return _live(query, variables)


def _live(query, variables):
    if query.startswith("query Context"):
        team = {"id": "team", "states": {"nodes": STATES}, "activeCycle": {"id": "cycle"}}
        statuses = [
            {"id": "started", "type": "started", "name": "In Progress"},
            {"id": "completed", "type": "completed", "name": "Completed"},
        ]
        return {"data": {"team": team, "organization": {"projectStatuses": statuses}}}
    if query.startswith("query Find"):
        page = {"nodes": [{"id": "project", "description": board.marker}], "pageInfo": {"hasNextPage": False}}
        return {"data": {"projects": page}}
    if query.startswith("query Milestones"):
        names = ("Specify", "Plan", "Tasks", "Implement", "Converge")
        nodes = [{"id": name[:1], "name": name} for name in names]
        return {"data": {"project": {"projectMilestones": {"nodes": nodes}}}}
    if query.startswith("query Issues"):
        page = {"nodes": board.issues, "pageInfo": {"hasNextPage": False}}
        return {"data": {"project": {"issues": page}}}
    raise AssertionError(query.split("{", 1)[0])


def enable(root, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "lin_test")
    path = root / ".cursor" / "cur-kit.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["linear"] = {"team": "ENG"}
    path.write_text(json.dumps(data), encoding="utf-8")
    board.calls, board.issues, board.marker = [], [], f"cur-kit:{root.name}"


def created(title):
    made = []
    for query, variables in board.calls:
        if query.startswith("mutation IssueCreate") and variables["input"]["title"].startswith(title):
            made.append(variables["input"])
    return made


def test_a_missing_key_queues_the_mcp_board_and_a_missing_team_does_nothing(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    board.calls = []
    sync(root, {"red": False}, board)
    path = root / ".cursor/cur-kit/state/linear-board.json"
    assert board.calls == [] and not path.exists()
    enable(root, monkeypatch)
    monkeypatch.delenv("LINEAR_API_KEY")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"issues": [{"key": "T099"}]}), encoding="utf-8")
    feature = root / "specs" / "001-login"
    feature.mkdir(parents=True)
    write(feature, "tasks.md", "- [ ] T014 [US1] Implement login\n")
    write(root, ".cursor/cur-kit/state/skill.json", json.dumps({"prompt": "/speckit-implement"}))
    sync(root, {"red": False}, board)
    saved = json.loads(path.read_text(encoding="utf-8"))
    task = next(item for item in saved["issues"] if item["key"] == "T014")
    assert board.calls == [] and saved["via"] == "linear-mcp" and saved["removedTasks"] == ["T099"]
    assert task["state"] == "In Progress" and task["cycle"] is True and saved["health"] == "onTrack"


def test_open_work_joins_the_cycle_and_backlog_stays_out(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    enable(root, monkeypatch)
    feature = root / "specs" / "001-login"
    feature.mkdir(parents=True)
    write(feature, "tasks.md", "- [ ] T014 [US1] Implement login in src/auth.py\n")
    write(root, ".cursor/cur-kit/state/skill.json", json.dumps({"prompt": "/speckit-implement"}))
    sync(root, {"red": False, "configured": True}, board)
    task, spec = created("[T014]")[0], created("[specification]")[0]
    assert task["stateId"] == "doing" and task["cycleId"] == "cycle" and task["priority"] == 2
    assert spec["stateId"] == "backlog" and spec["cycleId"] is None and task["projectMilestoneId"] == "I"
    health = [item[1]["input"] for item in board.calls if item[0].startswith("mutation Health")]
    assert health == [{"projectId": "project", "health": "onTrack", "body": "cur-kit: suite on track"}]


def test_a_second_issue_with_the_same_key_is_marked_duplicate(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    enable(root, monkeypatch)
    feature = root / "specs" / "001-login"
    feature.mkdir(parents=True)
    write(feature, "tasks.md", "- [ ] T014 [US1] Implement login\n")
    board.issues = [
        {"id": "later", "title": "[T014] later", "createdAt": "2024-01-01"},
        {"id": "early", "title": "[T014] early", "createdAt": "2020-01-01"},
    ]
    sync(root, {"red": False}, board)
    dupes = [item[1]["input"] for item in board.calls if item[0].startswith("mutation Duplicate")]
    assert dupes == [{"type": "duplicate", "issueId": "later", "relatedIssueId": "early"}]


def test_a_removed_task_is_canceled(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    enable(root, monkeypatch)
    feature = root / "specs" / "001-login"
    feature.mkdir(parents=True)
    write(feature, "tasks.md", "- [ ] T014 [US1] Implement login\n")
    record = {"prompt": "/speckit-converge", "response": "Converged."}
    write(root, ".cursor/cur-kit/state/skill.json", json.dumps(record))
    board.issues = [{"id": "gone", "title": "[T099] retired", "createdAt": "2020-01-01"}]
    sync(root, {"red": True}, board)
    sync(root, {"red": False}, board)
    updates = [item for item in board.calls if item[0].startswith("mutation IssueUpdate")]
    gone = [item[1] for item in updates if item[1]["id"] == "gone"]
    assert gone[0]["input"]["stateId"] == "canceled" and gone[0]["input"]["cycleId"] is None
    posted = [item[1]["input"] for item in board.calls if item[0].startswith("mutation Project")]
    assert [item["statusId"] for item in posted] == ["started", "completed"]


def test_a_linear_failure_does_not_change_the_stop_followup(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    enable(root, monkeypatch)
    down = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("down"))
    monkeypatch.setattr("curkit.linear_sync.graphql", down)
    payload = {"status": "completed", "loop_count": 0, "workspace_roots": [str(root)]}
    assert "followup_message" in on_stop(payload)
    logged = (root / ".cursor" / "cur-kit" / "state" / "runs.jsonl").read_text(encoding="utf-8")
    assert "Linear:" in logged and "RuntimeError" in logged
