"""AC-02: parse_tasks and open_tasks (tasks_citing is in test_tasks_2.py)."""

from __future__ import annotations

import pytest

from curkit.tasks import Task, open_tasks, parse_tasks

TASKS_MD = """\
# Tasks: Login

## Phase 1: Setup

- [X] T001 Create project structure per implementation plan
- [x] T002 [P] Configure linting in pyproject.toml

## Phase 3: User Story 1

**Goal**: users can log in

- [ ] T012 [P] [US1] Create User model in src/models/user.py
- [x] T013 [US1] Add login form in `src/ui/login.py` and tests/test_login.py.
- [ ] Create User model
T003 [US1] Create model without a checkbox
- Depends on T001

## Phase 4: User Story 2

- [ ] T020 [US2] Export report in src/export.py

## Phase 5: Convergence

- [ ] T042 Add export per US2/AC1 (missing)
- [ ] T043 Validate email format per FR-003 (partial)
"""


@pytest.fixture
def tasks() -> list[Task]:
    return parse_tasks(TASKS_MD)


def _by_id(tasks: list[Task], task_id: str) -> Task:
    return next(task for task in tasks if task.id == task_id)


def test_ac02_parse_tasks_reads_speckit_lines(tasks: list[Task]):
    task = _by_id(tasks, "T012")
    assert task == Task(
        id="T012",
        done=False,
        story="US1",
        keys=("US1",),
        paths=("src/models/user.py",),
        text="T012 [P] [US1] Create User model in src/models/user.py",
    )


def test_ac02_parse_tasks_reads_converge_lines(tasks: list[Task]):
    task = _by_id(tasks, "T042")
    assert (task.done, task.story, task.keys, task.paths) == (False, None, ("US2/AC1",), ())
    assert task.text == "T042 Add export per US2/AC1 (missing)"
    assert _by_id(tasks, "T043").keys == ("FR-003",)


def test_ac02_parse_tasks_ignores_non_task_lines(tasks: list[Task]):
    assert [task.id for task in tasks] == ["T001", "T002", "T012", "T013", "T020", "T042", "T043"]


def test_ac02_parse_tasks_handles_upper_and_lower_x(tasks: list[Task]):
    assert _by_id(tasks, "T001").done is True
    assert _by_id(tasks, "T002").done is True
    assert _by_id(tasks, "T013").done is True
    assert _by_id(tasks, "T012").done is False


def test_ac02_parse_tasks_collects_paths_without_punctuation(tasks: list[Task]):
    assert _by_id(tasks, "T013").paths == ("src/ui/login.py", "tests/test_login.py")
    assert _by_id(tasks, "T002").paths == ("pyproject.toml",)
    assert _by_id(tasks, "T001").paths == ()


def test_ac02_open_tasks_keeps_only_unchecked(tasks: list[Task]):
    assert [task.id for task in open_tasks(tasks)] == ["T012", "T020", "T042", "T043"]


def test_ac02_r13_marks_other_than_x_are_open():
    text = "- [-] T050 [US3] Half done in src/a.py\n- [~] T051 Waiting on src/b.py\n- [x] T052 Done\n- [ ] T053 Open\n"
    parsed = parse_tasks(text)
    assert [(task.id, task.done) for task in parsed] == [("T050", False), ("T051", False), ("T052", True), ("T053", False)]
    assert [task.id for task in open_tasks(parsed)] == ["T050", "T051", "T053"]
    assert (_by_id(parsed, "T050").story, _by_id(parsed, "T050").text) == ("US3", "T050 [US3] Half done in src/a.py")
