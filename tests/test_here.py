from __future__ import annotations

import subprocess

import pytest

from curkit.here import SeedError, seed

INIT = ["specify", "init", "--here", "--integration", "cursor-agent", "--non-interactive"]


def setup(tmp_path, monkeypatch, specify=True):
    folder = tmp_path / "bin"
    folder.mkdir()
    if specify:
        (folder / "specify").write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        (folder / "specify").chmod(0o755)
    monkeypatch.setenv("PATH", str(folder))
    root = tmp_path / "project"
    root.mkdir()
    return root


def recorder(calls: list, code: int = 0):
    return lambda argv, **kwargs: calls.append((argv, kwargs)) or subprocess.CompletedProcess(argv, code)


def test_ac12_seed_runs_no_specify_init_when_spec_kit_is_present(tmp_path, monkeypatch):
    root, calls = setup(tmp_path, monkeypatch), []
    (root / ".specify").mkdir()
    log = seed(root, runner=recorder(calls))
    assert calls == [] and not any(line.startswith("run ") for line in log)


def test_ac12_seed_runs_specify_init_in_an_empty_directory(tmp_path, monkeypatch):
    root, calls = setup(tmp_path, monkeypatch), []
    log = seed(root, runner=recorder(calls))
    assert calls == [(INIT, {"cwd": root})]
    assert log[0] == "run specify init --here --integration cursor-agent --non-interactive"


@pytest.mark.parametrize("entry", ["README.md", ".git/"])
def test_ac12_seed_adds_force_in_a_non_empty_directory(tmp_path, monkeypatch, entry):
    root, calls = setup(tmp_path, monkeypatch), []
    if entry.endswith("/"):
        (root / entry).mkdir()
    else:
        (root / entry).write_text("hello\n", encoding="utf-8")
    log = seed(root, runner=recorder(calls))
    assert calls == [([*INIT, "--force"], {"cwd": root})]
    assert log[0] == f"run {' '.join(INIT)} --force"


def test_ac12_seed_raises_an_install_hint_and_writes_nothing_when_specify_is_missing(tmp_path, monkeypatch):
    root, calls = setup(tmp_path, monkeypatch, specify=False), []
    with pytest.raises(SeedError, match="uv tool install specify-cli"):
        seed(root, runner=recorder(calls))
    assert calls == [] and list(root.iterdir()) == []


def test_ac12_seed_needs_no_specify_when_spec_kit_is_present(tmp_path, monkeypatch):
    root = setup(tmp_path, monkeypatch, specify=False)
    (root / ".specify").mkdir()
    log = seed(root, runner=recorder([]))
    assert "add .cursor/cur-kit.json" in log


def test_ac12_seed_stops_before_writing_when_specify_init_fails(tmp_path, monkeypatch):
    root = setup(tmp_path, monkeypatch)
    with pytest.raises(SeedError, match="exit code 2"):
        seed(root, runner=recorder([], code=2))
    assert list(root.iterdir()) == []
