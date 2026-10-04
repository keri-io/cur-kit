"""AC-04: the fingerprint follows tracked, untracked, HEAD, and salt changes, and nothing else."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from curkit.tree import fingerprint

SALT = "pytest -q"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    for key, value in (("user.email", "opus-a@example.com"), ("user.name", "Opus A"), ("commit.gpgsign", "false")):
        git(repo, "config", key, value)
    (repo / "app.py").write_text("x = 1\n")
    (repo / "logo.bin").write_bytes(b"\x00\x01")
    (repo / ".gitignore").write_text("*.log\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--no-verify", "-m", "init")
    return repo


def test_ac04_fingerprint_is_none_outside_a_git_work_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "app.py").write_text("x = 1\n")
    assert fingerprint(plain, SALT) is None
    assert fingerprint(make_repo(tmp_path) / ".git", SALT) is None


def test_ac04_fingerprint_is_a_stable_sha256_when_nothing_changes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    first = fingerprint(repo, SALT)
    (repo / "app.py").touch()
    assert first is not None and len(first) == 64 and int(first, 16) >= 0
    assert fingerprint(repo, SALT) == first


def test_ac04_fingerprint_changes_when_a_tracked_file_changes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    clean = fingerprint(repo, SALT)
    (repo / "app.py").write_text("x = 2\n")
    edited = fingerprint(repo, SALT)
    git(repo, "add", "app.py")
    staged = fingerprint(repo, SALT)
    (repo / "logo.bin").write_bytes(b"\x00\x02")
    binary = fingerprint(repo, SALT)
    assert clean != edited and clean != staged
    assert edited == staged, "staging alone leaves the files on disk, and so the key, unchanged"
    assert binary not in {clean, staged}


def test_ac04_fingerprint_changes_when_an_untracked_file_is_added_edited_or_renamed(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    clean = fingerprint(repo, SALT)
    (repo / "new.py").write_text("y = 1\n")
    added = fingerprint(repo, SALT)
    (repo / "new.py").write_text("y = 2\n")
    edited = fingerprint(repo, SALT)
    (repo / "new.py").rename(repo / "other.py")
    renamed = fingerprint(repo, SALT)
    assert len({clean, added, edited, renamed}) == 4


def test_ac04_fingerprint_changes_when_head_moves(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    before = fingerprint(repo, SALT)
    git(repo, "commit", "-q", "--no-verify", "--allow-empty", "-m", "empty")
    assert fingerprint(repo, SALT) != before


def test_ac04_fingerprint_changes_with_the_salt(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert fingerprint(repo, "pytest -q") != fingerprint(repo, "pytest -q -x")


def test_ac04_fingerprint_counts_an_untracked_nested_repo_without_failing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    clean = fingerprint(repo, SALT)
    git(repo, "init", "-q", "vendor/lib")
    (repo / "vendor/lib/lib.py").write_text("z = 1\n")
    nested = fingerprint(repo, SALT)
    assert isinstance(nested, str) and nested != clean


def test_ac04_fingerprint_ignores_gitignored_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    clean = fingerprint(repo, SALT)
    (repo / "debug.log").write_text("one\n")
    added = fingerprint(repo, SALT)
    (repo / "debug.log").write_text("two\n")
    assert clean == added == fingerprint(repo, SALT)
