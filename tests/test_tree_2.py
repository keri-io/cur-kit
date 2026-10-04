"""AC-04: fingerprint without commits, from a subfolder, past cur-kit state; changed_files."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from curkit.tree import changed_files, fingerprint

SALT = "pytest -q"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path: Path, commit: bool = True) -> Path:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    git(repo, "init", "-q")
    for key, value in (("user.email", "opus-a@example.com"), ("user.name", "Opus A"), ("commit.gpgsign", "false")):
        git(repo, "config", key, value)
    for name in ("app.py", "lib.py", "gone.py", "pkg/mod.py"):
        (repo / name).write_text(f"# {name}\n")
    (repo / ".gitignore").write_text("*.log\n")
    if commit:
        git(repo, "add", ".")
        git(repo, "commit", "-q", "--no-verify", "-m", "init")
    return repo


def test_ac04_fingerprint_works_in_a_repo_with_no_commits(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, commit=False)
    untracked = fingerprint(repo, SALT)
    git(repo, "add", "app.py")
    staged = fingerprint(repo, SALT)
    (repo / "app.py").write_text("x = 2\n")
    edited = fingerprint(repo, SALT)
    assert isinstance(untracked, str) and len(untracked) == 64
    assert len({untracked, staged, edited}) == 3


def test_ac04_fingerprint_skips_curkit_state_but_not_config(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    clean = fingerprint(repo, SALT)
    for state in (repo / ".cursor/cur-kit/state", repo / "pkg/.cursor/cur-kit/state"):
        state.mkdir(parents=True)
        (state / "runs.jsonl").write_text('{"ok": true}\n')
    assert fingerprint(repo, SALT) == clean
    (repo / ".cursor/cur-kit.json").write_text('{"test": "pytest -q"}\n')
    assert fingerprint(repo, SALT) != clean


def test_ac04_fingerprint_from_a_subfolder_covers_the_whole_repo(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    clean = fingerprint(repo / "pkg", SALT)
    assert clean == fingerprint(repo, SALT)
    (repo / "notes.md").write_text("outside pkg\n")
    assert fingerprint(repo / "pkg", SALT) != clean


def test_ac04_changed_files_lists_modified_staged_deleted_and_untracked_paths(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert changed_files(repo) == []
    (repo / "app.py").write_text("x = 2\n")
    (repo / "lib.py").write_text("y = 2\n")
    git(repo, "add", "lib.py")
    (repo / "gone.py").unlink()
    (repo / "pkg/new.py").write_text("z = 1\n")
    (repo / "debug.log").write_text("ignored\n")
    (repo / ".cursor/cur-kit/state").mkdir(parents=True)
    (repo / ".cursor/cur-kit/state/runs.jsonl").write_text("{}\n")
    assert changed_files(repo) == ["app.py", "gone.py", "lib.py", "pkg/new.py"]


def test_ac04_changed_files_are_relative_to_a_subfolder_root(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "app.py").write_text("x = 2\n")
    (repo / "pkg/mod.py").write_text("m = 2\n")
    (repo / "pkg/new.py").write_text("n = 1\n")
    assert changed_files(repo / "pkg") == ["mod.py", "new.py"]


def test_ac04_changed_files_in_a_repo_with_no_commits(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, commit=False)
    git(repo, "add", "app.py", "lib.py")
    (repo / "lib.py").write_text("y = 2\n")
    expected = [".gitignore", "app.py", "gone.py", "lib.py", "pkg/mod.py"]
    assert changed_files(repo) == expected


def test_ac04_without_git_on_path_there_is_no_fingerprint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_repo(tmp_path)
    (repo / "app.py").write_text("x = 2\n")
    monkeypatch.setenv("PATH", str(tmp_path / "no-bin"))
    assert fingerprint(repo, SALT) is None
    assert changed_files(repo) == []


def test_ac04_changed_files_is_empty_outside_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "app.py").write_text("x = 1\n")
    assert changed_files(plain) == []
