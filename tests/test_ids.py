"""AC-01: keys_in and story_of."""

from __future__ import annotations

import pytest

from curkit.ids import keys_in, story_of


def test_ac01_keys_in_finds_plain_text_keys_in_order():
    text = "Covers FR-003 and SC-002 for US1, scenario US1/AC2 in particular."
    assert keys_in(text) == ["FR-003", "SC-002", "US1", "US1/AC2"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("test_US1_AC2_x", ["US1/AC2"]),
        ("us1_ac2", ["US1/AC2"]),
        ("fr_003", ["FR-003"]),
        ("sc_002", ["SC-002"]),
        ("test_us3_login", ["US3"]),
    ],
)
def test_ac01_keys_in_reads_underscore_forms(name: str, expected: list[str]):
    assert keys_in(name) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("FR003", ["FR-003"]),
        ("SC002", ["SC-002"]),
        ("US1-AC2", ["US1/AC2"]),
        ("US1 AC2", ["US1/AC2"]),
        ("US12/AC3", ["US12/AC3"]),
    ],
)
def test_ac01_keys_in_reads_compact_hyphen_and_space_forms(text: str, expected: list[str]):
    assert keys_in(text) == expected


def test_ac01_keys_in_is_unique_and_canonical_in_first_seen_order():
    text = "us1_ac2 then FR003 then US1/AC2 again, fr-003 too, and US1-AC2"
    assert keys_in(text) == ["US1/AC2", "FR-003"]


@pytest.mark.parametrize("text", ["BUS1", "xFR-003", "FR-0031", "SC-0020", "US1x", "FR-003a", "User", "US"])
def test_ac01_keys_in_skips_other_words_and_longer_numbers(text: str):
    assert keys_in(text) == []


def test_ac01_keys_in_reads_pytest_node_ids_and_junit_names():
    assert keys_in("tests/test_auth.py::test_US1_AC2_redirects") == ["US1/AC2"]
    assert keys_in("tests.test_auth::test_fr_003_validates") == ["FR-003"]
    assert keys_in("login US1 AC2 redirects") == ["US1/AC2"]


def test_ac01_keys_in_reads_converge_and_task_lines():
    assert keys_in("- [ ] T042 Add export per US2/AC1 (missing)") == ["US2/AC1"]
    assert keys_in("- [ ] T012 [P] [US1] Create User model in src/models/user.py") == ["US1"]


def test_ac01_keys_in_empty_text_gives_no_keys():
    assert keys_in("") == []


def test_ac01_story_of_returns_the_story_or_none():
    assert story_of("US1/AC2") == "US1"
    assert story_of("US3") == "US3"
    assert story_of("US12/AC10") == "US12"
    assert story_of("FR-003") is None
    assert story_of("SC-002") is None
    assert story_of("") is None
