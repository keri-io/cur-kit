"""AC-02: tasks_citing (exact key match first, else the same story)."""

from __future__ import annotations

import pytest

from curkit.tasks import Task, parse_tasks, tasks_citing
from tests.test_tasks import TASKS_MD


@pytest.fixture
def tasks() -> list[Task]:
    return parse_tasks(TASKS_MD)


def test_ac02_tasks_citing_prefers_exact_key_matches(tasks: list[Task]):
    assert [task.id for task in tasks_citing(tasks, ["US2/AC1"])] == ["T042"]
    assert [task.id for task in tasks_citing(tasks, ["FR-003"])] == ["T043"]
    assert [task.id for task in tasks_citing(tasks, ["US1"])] == ["T012", "T013"]


def test_ac02_tasks_citing_falls_back_to_the_same_story(tasks: list[Task]):
    assert [task.id for task in tasks_citing(tasks, ["US1/AC2"])] == ["T012", "T013"]
    assert [task.id for task in tasks_citing(tasks, ["US2/AC9"])] == ["T020", "T042"]


def test_ac02_tasks_citing_merges_keys_in_task_order_without_unknown_keys(tasks: list[Task]):
    assert [task.id for task in tasks_citing(tasks, ["FR-003", "US1/AC2"])] == ["T012", "T013", "T043"]
    assert tasks_citing(tasks, ["FR-999", "US9"]) == []
    assert tasks_citing(tasks, []) == []
