"""Spec Kit's own long forms: spec headings say "User Story N", and converge cites AC1."""

from __future__ import annotations

import pytest

from curkit.ids import keys_in


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("per FR-009 and User Story 4 AC1 (missing)", ["FR-009", "US4/AC1"]),
        ("User Story 12 acceptance scenario 3", ["US12/AC3"]),
        ("User Story 4, AC 1", ["US4/AC1"]),
        ("See User Story 2, then US2/AC1", ["US2", "US2/AC1"]),
    ],
)
def test_speckit_keys_in_reads_user_story_headings(text: str, expected: list[str]):
    assert keys_in(text) == expected


@pytest.mark.parametrize("text", ["User Stories and their scenarios", "User Storybook 4", "the fourth story"])
def test_speckit_keys_in_ignores_forms_spec_kit_does_not_write(text: str):
    assert keys_in(text) == []
