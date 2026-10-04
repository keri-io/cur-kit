"""R2: tracked_print follows HEAD and tracked changes only, so artifacts a suite writes don't block reuse."""

from __future__ import annotations

from pathlib import Path

import pytest

from curkit.tree import fingerprint, tracked_print
from tests.test_tree import SALT, git, make_repo


def test_r2_tracked_print_is_none_outside_a_git_work_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()
    assert tracked_print(plain, SALT) is None


def test_r2_tracked_print_changes_with_a_tracked_edit_head_or_salt(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    clean = tracked_print(repo, SALT)
    (repo / "app.py").write_text("x = 2\n")
    edited = tracked_print(repo, SALT)
    git(repo, "commit", "-q", "--no-verify", "-am", "edit")
    moved = tracked_print(repo, SALT)
    assert clean is not None and len({clean, edited, moved}) == 3
    assert tracked_print(repo, "other") != moved


def test_r2_tracked_print_ignores_untracked_files_that_fingerprint_counts(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    tracked, full = tracked_print(repo, SALT), fingerprint(repo, SALT)
    (repo / "report.xml").write_text("<testsuites/>\n")
    assert tracked_print(repo, SALT) == tracked
    assert fingerprint(repo, SALT) != full
