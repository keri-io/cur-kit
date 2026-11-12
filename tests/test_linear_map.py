"""Status, priority, and cycle flags for the Linear board."""

from __future__ import annotations

import subprocess

from curkit.linear_map import build, repo_key, repo_name

TASKS = """\
## Phase 1: Foundational
- [ ] T014 [US1] Implement login in src/auth.py
- [x] T015 [US2] Add logout in src/logout.py
- [-] T016 Drop legacy login
- [ ] T017 [US2] HIGH rate limit
- [ ] T018 [US3] LOW copy tweak
## Phase 2: Convergence
- [ ] T042 CRITICAL constitution breach per US1/AC2
"""


def layout(tmp_path):
    root = tmp_path / "Corund"
    feature = root / "specs" / "001-login"
    feature.mkdir(parents=True)
    (feature / "tasks.md").write_text(TASKS, encoding="utf-8")
    (feature / "checklists").mkdir()
    (feature / "checklists" / "ux.md").write_text("# UX\n", encoding="utf-8")
    return root, feature


def card(root, key, **record):
    found = [item for item in build(root, record, record.pop("red", False)) if item.key == key]
    return found[0]


def test_a_new_spec_is_backlog_and_an_open_task_is_todo(tmp_path):
    root, _feature = layout(tmp_path)
    (root / ".specify/memory").mkdir(parents=True)
    (root / ".specify/memory/constitution.md").write_text("CRITICAL rules\n", encoding="utf-8")
    spec, task = card(root, "specification"), card(root, "T014")
    rules, research = card(root, "constitution"), card(root, "research")
    assert spec.status == "Backlog" and spec.cycle is False and spec.milestone == "Specify"
    assert (task.status, task.priority, task.cycle) == ("Todo", 2, False)
    assert rules.priority == 3 and rules.document.startswith("CRITICAL")
    assert research.priority == 4 and research.status == "Backlog"


def test_implement_puts_open_tasks_on_the_cycle(tmp_path):
    root, _feature = layout(tmp_path)
    task = card(root, "T014", prompt="/speckit-implement")
    assert task.status == "In Progress" and task.cycle is True and task.milestone == "Implement"
    reply = "Gap remains.\n/speckit-implement"
    again = card(root, "T014", prompt="/speckit-converge", response=reply)
    assert again.status == "In Progress" and again.cycle is True
    kept = card(root, "T014", prompt="Please run\n/speckit-converge\nsee speckit-implement")
    assert kept.status == "Todo"


def test_checked_tasks_stay_in_review_until_converge_confirms(tmp_path):
    root, feature = layout(tmp_path)
    (feature / "spec.md").write_text("# Spec\n", encoding="utf-8")
    waiting = card(root, "T015", prompt="/speckit-implement")
    assert waiting.status == "In Review" and waiting.cycle is True
    finished = card(
        root, "T015", prompt="/speckit-converge",
        response="Converged — no further implement pass is needed.",
    )
    assert finished.status == "Done" and finished.cycle is False
    blocked = card(root, "T015", prompt="/speckit-converge", response="Converged.", red=True)
    assert blocked.status == "In Review"
    stray = card(root, "T015", prompt="/speckit-implement", response="converged")
    assert stray.status == "In Review"
    spec = card(root, "specification", prompt="/speckit-converge", response="implementation is complete")
    assert spec.status == "Done" and spec.body == "# Spec"


def test_a_bad_mark_is_canceled_and_a_critical_task_is_urgent(tmp_path):
    root, _feature = layout(tmp_path)
    dropped, gap = card(root, "T016"), card(root, "T042")
    high, low = card(root, "T017"), card(root, "T018")
    assert dropped.status == "Canceled" and dropped.cycle is False
    assert gap.priority == 1 and gap.milestone == "Converge" and "convergence" in gap.labels
    assert high.priority == 2 and low.priority == 4


def test_the_next_skill_is_in_progress_and_checklists_stay_low(tmp_path):
    root, _feature = layout(tmp_path)
    findings = card(root, "findings", prompt="/speckit-implement")
    listed, plan = card(root, "checklist:ux"), card(root, "plan", prompt="/speckit-implement")
    assert findings.status == "In Progress" and findings.cycle is True
    assert findings.milestone == "Converge" and findings.document == ""
    assert plan.status == "Backlog" and plan.milestone == "Plan"
    assert listed.priority == 4 and listed.milestone == "Tasks" and listed.status == "In Review"
    owed = card(root, "findings", prompt="/speckit-specify", owed=True)
    assert owed.status == "In Progress" and owed.cycle is True


def test_the_active_feature_folder_is_the_one_spec_kit_names(tmp_path, monkeypatch):
    root, _feature = layout(tmp_path)
    (root / "specs" / "002-later").mkdir()
    (root / ".specify").mkdir()
    monkeypatch.setenv("SPECIFY_FEATURE_DIRECTORY", "specs/001-login")
    assert card(root, "T014").status == "Todo"


def test_repo_name_comes_from_the_github_url(tmp_path):
    assert repo_name("https://github.com/keri-io/Corund.git", tmp_path) == "Corund"
    assert repo_name("git@github.com:keri-io/Corund.git", tmp_path) == "Corund"
    assert repo_name("", tmp_path) == tmp_path.name
    root, _feature = layout(tmp_path)
    assert repo_key(root) == "Corund"
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "git@github.com:keri-io/Corund.git"],
        check=True,
    )
    assert repo_key(root) == "git@github.com:keri-io/Corund.git"
