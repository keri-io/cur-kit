"""AC-08: the check-off guard."""

from __future__ import annotations

from curkit.guard import violations
from curkit.junit import Case
from curkit.tasks import Task, parse_tasks


def _task(task_id: str, story: str | None, done: bool = True) -> Task:
    label = f"[{story}] " if story else ""
    text = f"{task_id} {label}Do the work in src/{task_id.lower()}.py"
    return Task(id=task_id, done=done, story=story, keys=(story,) if story else (), paths=(), text=text)


def test_ac08_done_story_task_without_a_citing_case_is_flagged():
    cases = [Case(name="tests.test_auth::test_US1_AC2_redirects", failed=False)]
    assert violations([_task("T015", "US2")], cases) == ["T015 [US2] is checked, but no passing test cites US2."]


def test_ac08_passing_scenario_case_satisfies_the_story():
    cases = [Case(name="tests.test_auth::test_US1_AC2_redirects", failed=False)]
    assert violations([_task("T014", "US1")], cases) == []


def test_ac08_passing_story_case_satisfies_the_story():
    assert violations([_task("T014", "US1")], [Case(name="tests.test_auth::test_us1_login", failed=False)]) == []
    assert violations([_task("T014", "US1")], [Case(name="login US1 AC2 redirects", failed=False)]) == []


def test_ac08_failing_citing_case_is_flagged_with_task_story_and_case():
    cases = [
        Case(name="tests.test_auth::test_US1_AC1_renders", failed=False),
        Case(name="tests.test_auth::test_US1_AC2_redirects", failed=True),
    ]
    found = violations([_task("T014", "US1")], cases)
    assert found == ["T014 [US1] is checked, but a failing test cites US1: tests.test_auth::test_US1_AC2_redirects."]


def test_ac08_several_failing_cases_are_all_named():
    cases = [Case(name="a::test_US1_AC1", failed=True), Case(name="b::test_US1_AC2", failed=True)]
    assert violations([_task("T014", "US1")], cases) == [
        "T014 [US1] is checked, but failing tests cite US1: a::test_US1_AC1, b::test_US1_AC2."
    ]


def test_ac08_open_tasks_and_tasks_without_a_label_are_not_guarded():
    tasks = [_task("T012", "US1", done=False), _task("T001", None), _task("T042", None)]
    assert violations(tasks, []) == []


def test_ac08_another_story_does_not_count():
    cases = [Case(name="tests.test_auth::test_US12_AC1_x", failed=False), Case(name="t::test_FR_001", failed=False)]
    assert violations([_task("T014", "US1")], cases) == ["T014 [US1] is checked, but no passing test cites US1."]


def test_ac08_none_cases_means_skipped_and_empty_cases_flags_every_done_story_task():
    tasks = [_task("T014", "US1"), _task("T015", "US2"), _task("T001", None)]
    assert violations(tasks, None) is None
    assert violations(tasks, []) == [
        "T014 [US1] is checked, but no passing test cites US1.",
        "T015 [US2] is checked, but no passing test cites US2.",
    ]


def test_ac08_works_on_parsed_tasks_md():
    tasks = parse_tasks("- [x] T013 [US1] Add login form in src/ui/login.py\n- [ ] T020 [US2] Export in src/export.py\n")
    cases = [Case(name="tests.test_login::test_US1_AC1_form", failed=False)]
    assert violations(tasks, cases) == []
    assert violations(tasks, [Case(name="tests.test_login::test_US1_AC1_form", failed=True)]) == [
        "T013 [US1] is checked, but a failing test cites US1: tests.test_login::test_US1_AC1_form."
    ]
