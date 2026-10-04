"""Spec Kit tasks.md: checklist lines become Task records."""

from __future__ import annotations

import re
from dataclasses import dataclass

from curkit.ids import KEY, keys_in, story_of

LINE = re.compile(r"^\s*[-*+]\s+\[([^\]])\]\s*((T\d+)\b.*)$")
DONE_MARKS = ("x", "X")
LABEL = re.compile(r"\[(US\d+)\]")
EXTENSION = re.compile(r"\.[A-Za-z]\w*$")
TRIM = "`'\"()[]{}<>,;:"


@dataclass(frozen=True)
class Task:
    id: str
    done: bool
    story: str | None
    keys: tuple[str, ...]
    paths: tuple[str, ...]
    text: str


def _is_path(token: str) -> bool:
    looks_like_path = "/" in token or EXTENSION.search(token) is not None
    return looks_like_path and KEY.fullmatch(token) is None


def paths_in(text: str) -> tuple[str, ...]:
    """File paths named in a task line, e.g. src/models/user.py, without surrounding punctuation."""
    tokens = (word.rstrip(TRIM + ".").lstrip(TRIM) for word in text.split())
    return tuple(dict.fromkeys(token for token in tokens if token and _is_path(token)))


def _task(match: re.Match[str]) -> Task:
    mark, text, task_id = match.groups()
    text = text.strip()
    label = LABEL.search(text)
    return Task(
        id=task_id,
        done=mark in DONE_MARKS,
        story=label[1] if label else None,
        keys=tuple(keys_in(text)),
        paths=paths_in(text),
        text=text,
    )


def parse_tasks(text: str) -> list[Task]:
    """Tasks from Spec Kit and converge checklist lines; other lines are ignored."""
    return [_task(match) for match in map(LINE.match, text.splitlines()) if match]


def open_tasks(tasks: list[Task]) -> list[Task]:
    return [task for task in tasks if not task.done]


def _stories(task: Task) -> set[str]:
    return {story for story in map(story_of, task.keys) if story}


def tasks_citing(tasks: list[Task], keys: list[str]) -> list[Task]:
    """Tasks citing a key exactly; for keys nobody cites, tasks of the same story. Task order."""
    chosen: set[Task] = set()
    for key in keys:
        exact = [task for task in tasks if key in task.keys]
        chosen.update(exact or [task for task in tasks if story_of(key) in _stories(task)])
    return [task for task in tasks if task in chosen]
