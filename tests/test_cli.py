"""AC-18 and AC-21: `cur-kit check`, --version, install, --here, and bin/cur-kit through symlinks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from curkit import __version__
from curkit.__main__ import main
from tests.test_check import FAILING, make_project, write

BIN = Path(__file__).resolve().parent.parent / "bin" / "cur-kit"
VERSION = f"cur-kit {__version__}"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """No CLI test may reach the real home folder or the outer Cursor project."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)


def cli(cwd: Path, *args: str, exe: Path = BIN) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(exe), *args], cwd=cwd, capture_output=True, text=True, timeout=120, check=False)


def test_ac18_check_prints_the_result_as_json_and_exits_0_even_when_red(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(make_project(tmp_path))
    assert main(["check"]) == 0
    out = capsys.readouterr().out
    result = json.loads(out)
    assert result["red"] and result["failing"] == [FAILING] and len(out.splitlines()) > 1


def test_ac18_check_json_prints_the_result_on_one_line_through_bin_cur_kit(tmp_path):
    root = make_project(tmp_path)
    done = cli(root, "check", "--json")
    assert done.returncode == 0 and len(done.stdout.splitlines()) == 1, done.stderr
    result = json.loads(done.stdout)
    assert (result["red"], result["open"], result["ids"]) == (True, 0, ["US1/AC2"])
    assert json.loads(cli(root, "check", "--json").stdout)["reused"]


def test_ac21_version_prints_the_version(tmp_path, capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0 and capsys.readouterr().out.strip() == VERSION
    done = cli(tmp_path, "--version")
    assert (done.returncode, done.stdout.strip()) == (0, VERSION)


def test_ac21_bin_cur_kit_works_through_a_symlink_from_another_directory(tmp_path):
    link = tmp_path / "home" / ".local" / "bin" / "cur-kit"
    link.parent.mkdir(parents=True)
    link.symlink_to(BIN)
    chained = tmp_path / "links" / "ck"
    chained.parent.mkdir()
    chained.symlink_to(link)
    elsewhere = tmp_path / "elsewhere"
    write(elsewhere, "json.py", "raise SystemExit('the project shadowed the stdlib json')\n")
    version = cli(elsewhere, "--version", exe=chained)
    assert (version.returncode, version.stdout.strip()) == (0, VERSION), version.stderr
    assert cli(elsewhere, "install", "--home", str(tmp_path / "h"), exe=chained).returncode == 0
    hooks = json.loads((tmp_path / "h" / ".cursor" / "hooks.json").read_text())["hooks"]
    assert hooks["stop"][0]["command"] == f"{BIN} hook stop --user"


def test_ac21_install_installs_the_hooks_and_the_bin_link(tmp_path, capsys):
    home = tmp_path / "custom"
    assert main(["install", "--home", str(home)]) == 0
    hooks = json.loads((home / ".cursor" / "hooks.json").read_text())["hooks"]
    assert hooks["stop"] == [{"command": f"{BIN} hook stop --user", "timeout": 900, "loop_limit": 25}]
    assert hooks["sessionStart"] == [{"command": f"{BIN} hook session-start", "timeout": 10}]
    link = home / ".local" / "bin" / "cur-kit"
    assert link.is_symlink() and link.readlink() == BIN
    lines = capsys.readouterr().out.splitlines()
    assert lines == [f"add stop hook: {BIN} hook stop --user", f"add sessionStart hook: {BIN} hook session-start",
                     f"link {link} -> {BIN}"]


def test_ac21_install_defaults_to_home_and_exits_1_when_hooks_json_cannot_be_merged(tmp_path, capsys):
    assert main(["install"]) == 0
    assert (tmp_path / "home" / ".cursor" / "hooks.json").is_file()
    assert (tmp_path / "home" / ".local" / "bin" / "cur-kit").readlink() == BIN
    broken = write(tmp_path / "broken", ".cursor/hooks.json", "{broken")
    capsys.readouterr()
    assert main(["install", "--home", str(tmp_path / "broken")]) == 1
    assert "not valid JSON" in capsys.readouterr().err
    assert broken.read_text() == "{broken" and not (tmp_path / "broken" / ".local").exists()


def test_ac21_here_seeds_the_current_directory(tmp_path):
    root = tmp_path / "fresh"
    (root / ".specify").mkdir(parents=True)
    done = cli(root, "--here")
    assert done.returncode == 0 and "add .cursor/cur-kit.json" in done.stdout, done.stderr
    assert (root / ".cursor" / "cur-kit.json").is_file() and (root / ".cursor" / "cur-kit" / "workflow.yml").is_file()
    assert ".cursor/cur-kit/state/" in (root / ".gitignore").read_text()


def test_ac21_here_exits_1_with_the_install_hint_when_specify_is_missing(tmp_path, monkeypatch, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    monkeypatch.setenv("PATH", str(tmp_path / "no-bin"))
    assert main(["--here"]) == 1
    assert "uv tool install specify-cli" in capsys.readouterr().err
    assert list(empty.iterdir()) == []
