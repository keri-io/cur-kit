"""Check-off guard: a done [USn] task needs a passing test that cites USn or one of its scenarios."""

from __future__ import annotations

from curkit.ids import keys_in, story_of
from curkit.junit import Case
from curkit.tasks import Task


def _stories(case: Case) -> set[str]:
    return {story for story in map(story_of, keys_in(case.name)) if story}


def _message(task: Task, cited: list[Case]) -> str | None:
    head = f"{task.id} [{task.story}] is checked, but"
    if not cited:
        return f"{head} no passing test cites {task.story}."
    failing = [case.name for case in cited if case.failed]
    if failing:
        verb = "a failing test cites" if len(failing) == 1 else "failing tests cite"
        return f"{head} {verb} {task.story}: {', '.join(failing)}."
    if any(not case.skipped for case in cited):
        return None
    what = "the only test citing" if len(cited) == 1 else "every test citing"
    return f"{head} {what} {task.story} was skipped: {', '.join(case.name for case in cited)}."


def violations(tasks: list[Task], cases: list[Case] | None) -> list[str] | None:
    """One message per done story task without a passing (not failed, not skipped) citing test, or with a failing one.

    None when there is no JUnit report.
    """
    if cases is None:
        return None
    stories_by_case = [(case, _stories(case)) for case in cases]
    messages = []
    for task in tasks:
        if task.done and task.story:
            cited = [case for case, stories in stories_by_case if task.story in stories]
            messages.append(_message(task, cited))
    return [message for message in messages if message]
